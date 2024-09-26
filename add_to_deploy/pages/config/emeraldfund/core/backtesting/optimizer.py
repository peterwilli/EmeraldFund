import datetime
import subprocess
import traceback
from abc import ABC, abstractmethod
from typing import Tuple, Type, List

import optuna
from pydantic import BaseModel
from ..utils import create_slices_of_start_end_date
from core.backtesting import BacktestingEngine
from hummingbot.strategy_v2.controllers import ControllerConfigBase
import numpy as np


class BacktestingConfig(BaseModel):
    """
    A simple data structure to hold the backtesting configuration.
    """

    config: ControllerConfigBase
    resolution: str
    date_ranges: List[List[int]]


class BaseStrategyConfigGenerator(ABC):
    """
    Base class for generating strategy configurations for optimization.
    Subclasses should implement the method to provide specific strategy configurations.
    """

    def __init__(self, date_ranges: List[List[int]]):
        """
        Initialize with common parameters for backtesting.

        Args:
            date_ranges (List[List[int]]): A list of date ranges to backtest.
        """
        self.date_ranges = date_ranges

    @abstractmethod
    def generate_config(self, trial) -> BacktestingConfig:
        """
        Generate the configuration for a given trial.
        This method must be implemented by subclasses.

        Args:
            trial (optuna.Trial): The trial object containing hyperparameters to optimize.

        Returns:
            BacktestingConfig: An object containing the configuration, start time, and end time.
        """
        pass


class StrategyOptimizer:
    """
    Class for optimizing trading strategies using Optuna and a backtesting engine.
    """

    def __init__(
        self,
        storage_name: str,
        load_cached_data: bool = False,
    ):
        """
        Initialize the optimizer with a backtesting engine and database configuration.

        Args:
            root_path (str): Root path for storing database files.
            database_name (str): Name of the SQLite database for storing optimization results.
            load_cached_data (bool): Whether to load cached backtesting data.
        """
        self._backtesting_engine = BacktestingEngine(load_cached_data=load_cached_data)
        self._storage_name = storage_name
        self.dashboard_process = None

    def get_all_study_names(self):
        """
        Get all the study names available in the database.

        Returns:
            List[str]: A list of study names.
        """
        return optuna.get_all_study_names(self._storage_name)

    def get_study(self, study_name: str):
        """
        Get the study object for a given study name.

        Args:
            study_name (str): The name of the study.

        Returns:
            optuna.Study: The study object.
        """
        return optuna.load_study(study_name=study_name, storage=self._storage_name)

    def get_study_trials_df(self, study_name: str):
        """
        Get the trials data frame for a given study name.

        Args:
            study_name (str): The name of the study.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the trials data.
        """
        study = self.get_study(study_name)
        return study.trials_dataframe()

    def get_study_best_params(self, study_name: str):
        """
        Get the best parameters for a given study name.

        Args:
            study_name (str): The name of the study.

        Returns:
            Dict[str, Any]: A dictionary containing the best parameters.
        """
        study = self.get_study(study_name)
        return study.best_params

    def _create_study(
        self, study_name: str, load_if_exists: bool = True
    ) -> optuna.Study:
        """
        Create or load an Optuna study for optimization.

        Args:
            study_name (str): The name of the study.
            direction (str): Direction of optimization ("maximize" or "minimize").
            load_if_exists (bool): Whether to load an existing study if available.

        Returns:
            optuna.Study: The created or loaded study.
        """
        return optuna.create_study(
            directions=["maximize", "maximize"],
            study_name=study_name,
            storage=self._storage_name,
            load_if_exists=load_if_exists,
        )

    async def optimize(
        self,
        study_name: str,
        config_generator: Type[BaseStrategyConfigGenerator],
        n_trials: int = 100,
        load_if_exists: bool = True,
    ):
        """
        Run the optimization process asynchronously.

        Args:
            study_name (str): The name of the study.
            config_generator (Type[BaseStrategyConfigGenerator]): A configuration generator class instance.
            n_trials (int): Number of trials to run for optimization.
            load_if_exists (bool): Whether to load an existing study if available.
        """
        study = self._create_study(study_name, load_if_exists=load_if_exists)
        await self._optimize_async(study, config_generator, n_trials=n_trials)

    async def _optimize_async(
        self,
        study: optuna.Study,
        config_generator: Type[BaseStrategyConfigGenerator],
        n_trials: int,
    ):
        """
        Asynchronously optimize using the provided study and configuration generator.

        Args:
            study (optuna.Study): The study to use for optimization.
            config_generator (Type[BaseStrategyConfigGenerator]): A configuration generator class instance.
            n_trials (int): Number of trials to run for optimization.
        """
        for _ in range(n_trials):
            trial = study.ask()

            try:
                # Run the async objective function and get the result
                value = await self._async_objective(trial, config_generator)

                # Report the result back to the study
                study.tell(trial, value)

            except Exception as e:
                print(f"Error in _optimize_async: {str(e)}")
                study.tell(trial, state=optuna.trial.TrialState.FAIL)

    async def _async_objective(
        self, trial: optuna.Trial, config_generator: Type[BaseStrategyConfigGenerator]
    ) -> Tuple[float, float]:
        """
        The asynchronous objective function for a given trial.

        Args:
            trial (optuna.Trial): The trial object containing hyperparameters.
            config_generator (Type[BaseStrategyConfigGenerator]): A configuration generator class instance.

        Returns:
            float: The objective value to be optimized.
        """
        try:
            # Generate configuration using the config generator
            backtesting_config: BacktestingConfig = config_generator.generate_config(
                trial
            )

            max_drawdown_pct_list = []
            net_pnl_list = []
            for idx, date_range in enumerate(backtesting_config.date_ranges):
                backtesting_result = await self._backtesting_engine.run_backtesting(
                    backtesting_config.config,
                    date_range[0],
                    date_range[1],
                    backtesting_config.resolution,
                )
                strategy_analysis = backtesting_result.results
                max_drawdown_pct = strategy_analysis["max_drawdown_pct"]
                net_pnl = strategy_analysis["net_pnl"]
                max_drawdown_pct_list.append(max_drawdown_pct)
                net_pnl_list.append(net_pnl)
                if idx == 0:
                    trial.set_user_attr(
                        "config", backtesting_result.controller_config.json()
                    )
            net_pnl = sum(net_pnl_list) / len(net_pnl_list)
            max_drawdown_pct = max(max_drawdown_pct_list) / len(max_drawdown_pct_list)

            # Return the value you want to optimize
            return max_drawdown_pct, net_pnl
        except Exception as e:
            print(f"An error occurred during optimization: {str(e)}")
            traceback.print_exc()
            return float("-inf"), float(
                "-inf"
            )  # Return a very low value to indicate failure

    def launch_optuna_dashboard(self):
        """
        Launch the Optuna dashboard for visualization.
        """
        self.dashboard_process = subprocess.Popen(
            ["optuna-dashboard", self._storage_name]
        )

    def kill_optuna_dashboard(self):
        """
        Kill the Optuna dashboard process.
        """
        if self.dashboard_process and self.dashboard_process.poll() is None:
            self.dashboard_process.terminate()  # Graceful termination
            self.dashboard_process.wait()  # Wait for process to terminate
            self.dashboard_process = None  # Reset process handle
        else:
            print("Dashboard is not running or already terminated.")
