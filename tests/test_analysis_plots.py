import unittest
from unittest.mock import patch

import matplotlib.pyplot as plt

from nimo.analysis.statements import _save_or_show


class SaveOrShowTests(unittest.TestCase):
    def test_show_uses_blocking_display(self) -> None:
        fig = plt.figure()
        with patch("matplotlib.pyplot.show") as show_mock:
            _save_or_show(fig, None, True)
        show_mock.assert_called_once_with(block=True)


if __name__ == "__main__":
    unittest.main()
