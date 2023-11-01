#!/usr/bin/env bash
# Copyright (c) 2018-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

set -ex

# Missing libffi on aarch64
if [ -x /usr/bin/yum ]; then
    yum install -y libffi-devel
fi

if [ -e /tmp/wheels ]; then
    echo "/tmp/wheels should not exist!"
    exit 1
fi

mkdir -p /tmp/wheels

${PYPATH}/bin/python -m pip wheel -v /project -w /tmp/wheels --no-deps
wheel=$(ls /tmp/wheels/*.whl)

# Apply fixups.
auditwheel repair ${wheel} -w /project/dist
