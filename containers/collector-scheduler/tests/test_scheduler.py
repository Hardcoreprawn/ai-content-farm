import main as scheduler_main
import sys
import os
import json
from unittest.mock import patch, Mock

# Ensure the scheduler dir is importable when pytest's root is the repo root
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))


def test_run_once_posts_to_collector(monkeypatch):
    mock_post = Mock()
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    monkeypatch.setattr(scheduler_main, 'post_collect', mock_post)

    mock_write = Mock()
    mock_write.return_value = 'http://blob/run-manifests/run_test.json'
    monkeypatch.setattr(scheduler_main, 'write_run_manifest', mock_write)

    rc = scheduler_main.run_once()

    assert mock_post.called
    assert mock_write.called
    assert rc == 0
