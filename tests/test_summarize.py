from unittest.mock import patch

import pytest

from zvi_summaries.summarize import MissingOpenRouterKeyError, environment_api_key


def test_environment_api_key_missing() -> None:
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(MissingOpenRouterKeyError):
            environment_api_key()
