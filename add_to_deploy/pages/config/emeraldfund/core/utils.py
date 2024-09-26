from typing import List
import random


def round_to_nearest_day(timestamp):
    return round(timestamp / 86400) * 86400


def create_slices_of_start_end_date(
    start: int, end: int, amount_of_slices: int, days_gap: int, jitter: int = 0
) -> List[List[int]]:
    """
    Creates even sections between the start and end date with optional jitter.

    Args:
    start (int): The start date in unix timestamp.
    end (int): The end date in unix timestamp.
    amount_of_slices (int): The number of slices to create.
    days_gap (int): The gap in days between each slice.
    jitter (int, optional): The maximum number of days to randomly add or subtract from each slice. Defaults to 0.

    Returns:
    List[List[int]]: A list of slices, where each slice is a list containing the start and end date.
    """

    # Calculate the total duration
    total_duration = end - start

    # Calculate the duration of each slice without the gap
    slice_duration = (
        total_duration - (amount_of_slices - 1) * days_gap * 86400
    ) // amount_of_slices

    # Calculate the remaining seconds after creating all slices
    remaining_seconds = (
        total_duration
        - slice_duration * amount_of_slices
        - (amount_of_slices - 1) * days_gap * 86400
    )

    # Initialize the list of slices
    slices = []

    # Initialize the current start date
    current_start = start

    # Create each slice
    for i in range(amount_of_slices):
        # Calculate the current end date
        current_end = current_start + slice_duration

        # Add the remaining seconds to the last slice
        if i == amount_of_slices - 1:
            current_end += remaining_seconds

        # Apply jitter to the slice
        if jitter > 0:
            jitter_in_seconds = jitter * 86400
            current_start += random.randint(-jitter_in_seconds, jitter_in_seconds)
            current_end += random.randint(-jitter_in_seconds, jitter_in_seconds)

        # Ensure the start date is before the end date
        if current_start >= current_end:
            raise ValueError("The start date must be before the end date")

        # Round the dates to the nearest day
        result_start = round_to_nearest_day(current_start)
        result_end = round_to_nearest_day(current_end)

        # Add the slice to the list
        slices.append([result_start, result_end])

        # Update the current start date
        current_start = current_end + days_gap * 86400

    return slices

