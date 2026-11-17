# CI diagnostic: unit-test loop as pages.yml runs it

- generated_utc: 2026-11-17T16:30:41Z
- runner: ubuntu26 / 20261111.196.1
- python: Python 3.14.4  (path: /usr/bin/python3)
- pip list (third-party, first 40):
    Package                   Version
    ------------------------- ---------------
    argcomplete               3.7.2
    attrs                     25.4.0
    autocommand               2.2.2
    Automat                   25.4.16
    babel                     2.17.0
    bcc                       0.35.0
    bcrypt                    5.0.0
    blinker                   1.9.0
    boto3                     1.40.72
    botocore                  1.40.72
    certifi                   2026.1.4
    chardet                   5.2.0
    click                     8.1.8
    command-not-found         0.3
    configobj                 5.0.9
    constantly                23.10.4
    crit                      4.2
    cryptography              46.0.5
    dbus-python               1.4.0
    distro                    1.9.0
    distro-info               1.15+ubuntu0.1
    filelock                  4.2.10
    httplib2                  0.22.0
    hyperlink                 21.0.0
    idna                      3.11
    incremental               24.7.2
    inflect                   7.5.0
    jaraco.context            6.0.1
    jaraco.functools          4.1.0
    jaraco.text               4.0.0
    Jinja2                    3.1.6
    jmespath                  1.0.1
    jsonpatch                 1.32
    jsonpointer               2.4
    jsonschema                4.19.2
    jsonschema-specifications 2023.12.1
    launchpadlib              2.1.0
    lazr.restfulclient        0.14.6

```
PASS  scripts.test_capture_official_ca442d3d
FAIL  scripts.test_gate_roundtrip
      
      ----------------------------------------------------------------------
      Ran 0 tests in 0.000s
      
      NO TESTS RAN
PASS  scripts.test_injury_diff
PASS  scripts.test_injury_edition_crosscheck_07920bdc
PASS  scripts.test_minutes_shares
PASS  scripts.test_noise_band_refusal
PASS  scripts.test_parse_official
PASS  scripts.test_promote_official
PASS  scripts.test_refresh_gate
PASS  scripts.test_refresh_workflow
```
