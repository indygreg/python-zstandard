IF "%CONDA%" == "1" (
    CALL conda build ci\\conda || EXIT 1
    CALL python ci\copy-conda-package.py || EXIT 1
) ELSE (
    CALL %PYTHON%\\Scripts\\tox || EXIT 1
)
