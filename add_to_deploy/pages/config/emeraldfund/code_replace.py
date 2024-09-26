import re
import pprint

RE_GET_PARAMETERS = re.compile(
    r"def get_parameters\(self\):\s*return ({.*?})\s*$", re.DOTALL | re.MULTILINE
)


def code_replace(processor_code: str, obj):
    obj_str = pprint.pformat(obj, width=100, indent=4)
    replacement = f"def get_parameters(self):\n        return {obj_str}\n"
    modified_text = RE_GET_PARAMETERS.sub(replacement, processor_code)
    return modified_text


def test():
    with open("algo_test.py", "r") as f:
        test_code = f.read()
        print(code_replace(test_code, {"test": 1}))


if __name__ == "__main__":
    test()
