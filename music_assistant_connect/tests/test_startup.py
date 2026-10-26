import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import startup


def test_bootstrap_loads_before_drop_and_keeps_options_in_memory(monkeypatch):
    import main
    import uvicorn
    events=[]
    config={'ma_url':'http://192.168.1.5:8095','ma_token':'test-secret'}
    def load():
        events.append('load')
        return config
    def drop():
        assert events==['load']
        events.append('drop')
    def serve(app, **kwargs):
        assert events==['load','drop']
        assert main.options()==config
        assert kwargs['proxy_headers'] is False
        events.append('serve')
    monkeypatch.setattr(main,'APP_OPTIONS',None)
    monkeypatch.setattr(startup,'load_options',load)
    monkeypatch.setattr(startup,'drop_privileges',drop)
    monkeypatch.setattr(uvicorn,'run',serve)
    startup.main()
    assert events==['load','drop','serve']


def test_bootstrap_rejects_invalid_config_without_logging_secret(tmp_path, monkeypatch, capsys):
    path=tmp_path/'options.json'
    path.write_text('{"ma_token":"do-not-print",broken}', encoding='utf-8')
    original_load=startup.load_options
    monkeypatch.setattr(startup,'load_options',lambda:original_load(path))
    # Test the reader directly: malformed JSON must never become an empty config.
    with pytest.raises(SystemExit) as error:
        startup.main()
    assert 'do-not-print' not in str(error.value)
    assert 'do-not-print' not in capsys.readouterr().out
