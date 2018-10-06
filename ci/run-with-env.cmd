:: Note: this script needs to be run with the /E:ON and /V:ON flags for the
:: cmd interpreter, at least for (SDK v7.0)
::
:: More details at:
:: https://github.com/cython/cython/wiki/64BitCythonExtensionsOnWindows
:: http://stackoverflow.com/a/13751649/163740
::
:: Author: Olivier Grisel
:: License: CC0 1.0 Universal: http://creativecommons.org/publicdomain/zero/1.0/
@ECHO OFF

SET COMMAND_TO_RUN=%*
SET WIN_SDK_ROOT=C:\Program Files\Microsoft SDKs\Windows
SET WIN_WDK=c:\Program Files (x86)\Windows Kits\10\Include\wdf

:: Extract the major and minor versions, and allow for the minor version to be
:: more than 9.  This requires the version number to have two dots in it.
SET MAJOR_PYTHON_VERSION=%PYTHON_VERSION:~0,1%
IF "%PYTHON_VERSION:~3,1%" == "." (
    SET MINOR_PYTHON_VERSION=%PYTHON_VERSION:~2,1%
) ELSE (
    SET MINOR_PYTHON_VERSION=%PYTHON_VERSION:~2,2%
)

:: Modern versions of distutils attempt to guess the toolchain to use based
:: on ``sys.version`` and from inspecting the system (notably the registry).
:: This is somewhat fragile in AppVeyor for some reason. So, we instead set
:: ``DISTUTILS_USE_SDK`` and ``MSSdk`` along with some other environment
:: variables (some set by ``vcvarsall.bat``) to force distutils to use a
:: specific toolchain and SDK.

IF %MAJOR_PYTHON_VERSION% == 2 (
    SET WINDOWS_SDK_VERSION="v7.0"
    SET TOOLS_VERSION="9.0"
    SET VCVARS=vcvars64.bat
) ELSE (
    IF %MAJOR_PYTHON_VERSION% == 3 (
        SET WINDOWS_SDK_VERSION="v7.1"

        IF %MINOR_PYTHON_VERSION% LEQ 4 (
            SET WINDOWS_SDK_VERSION="v7.1"
            SET TOOLS_VERSION="10.0"
            SET VCVARS=amd64\vcvars64.bat
        ) ELSE (
            SET WINDOWS_SDK_VERSION="v7.1"
            SET TOOLS_VERSION="14.0"
            SET VCVARS=amd64\vcvars64.bat
        )

        IF EXIST "%WIN_WDK%" (
            :: See: https://connect.microsoft.com/VisualStudio/feedback/details/1610302/
            REN "%WIN_WDK%" 0wdf
        )
    )
)

SET DISTUTILS_USE_SDK=1
SET MSSdk=1
"%WIN_SDK_ROOT%\%WINDOWS_SDK_VERSION%\Setup\WindowsSdkVer.exe" -q -version:%WINDOWS_SDK_VERSION%

if %PYTHON_ARCH% == 64 (
    CALL "C:\Program Files (x86)\Microsoft Visual Studio %TOOLS_VERSION%\VC\bin\%VCVARS%" || EXIT 1
    ECHO Executing: %COMMAND_TO_RUN%
    CALL %COMMAND_TO_RUN% || EXIT 1
) ELSE (
    CALL "C:\Program Files (x86)\Microsoft Visual Studio %TOOLS_VERSION%\VC\vcvarsall.bat" x86 || EXIT 1
    ECHO Executing: %COMMAND_TO_RUN%
    CALL %COMMAND_TO_RUN% || EXIT 1
)
