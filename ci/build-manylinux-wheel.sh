#!/usr/bin/env bash
# Copyright (c) 2018-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

set -ex

# Missing libffi on aarch64
yum install -y libffi-devel

if [ -e /tmp/wheels ]; then
    echo "/tmp/wheels should not exist!"
    exit 1
fi

cat > /tmp/requirements.txt << EOF
cffi==1.14.5 \
    --hash=sha256:005a36f41773e148deac64b08f233873a4d0c18b053d37da83f6af4d9087b813 \
    --hash=sha256:0857f0ae312d855239a55c81ef453ee8fd24136eaba8e87a2eceba644c0d4c06 \
    --hash=sha256:1071534bbbf8cbb31b498d5d9db0f274f2f7a865adca4ae429e147ba40f73dea \
    --hash=sha256:158d0d15119b4b7ff6b926536763dc0714313aa59e320ddf787502c70c4d4bee \
    --hash=sha256:1f436816fc868b098b0d63b8920de7d208c90a67212546d02f84fe78a9c26396 \
    --hash=sha256:2894f2df484ff56d717bead0a5c2abb6b9d2bf26d6960c4604d5c48bbc30ee73 \
    --hash=sha256:29314480e958fd8aab22e4a58b355b629c59bf5f2ac2492b61e3dc06d8c7a315 \
    --hash=sha256:34eff4b97f3d982fb93e2831e6750127d1355a923ebaeeb565407b3d2f8d41a1 \
    --hash=sha256:35f27e6eb43380fa080dccf676dece30bef72e4a67617ffda586641cd4508d49 \
    --hash=sha256:3d3dd4c9e559eb172ecf00a2a7517e97d1e96de2a5e610bd9b68cea3925b4892 \
    --hash=sha256:43e0b9d9e2c9e5d152946b9c5fe062c151614b262fda2e7b201204de0b99e482 \
    --hash=sha256:48e1c69bbacfc3d932221851b39d49e81567a4d4aac3b21258d9c24578280058 \
    --hash=sha256:51182f8927c5af975fece87b1b369f722c570fe169f9880764b1ee3bca8347b5 \
    --hash=sha256:58e3f59d583d413809d60779492342801d6e82fefb89c86a38e040c16883be53 \
    --hash=sha256:5de7970188bb46b7bf9858eb6890aad302577a5f6f75091fd7cdd3ef13ef3045 \
    --hash=sha256:65fa59693c62cf06e45ddbb822165394a288edce9e276647f0046e1ec26920f3 \
    --hash=sha256:69e395c24fc60aad6bb4fa7e583698ea6cc684648e1ffb7fe85e3c1ca131a7d5 \
    --hash=sha256:6c97d7350133666fbb5cf4abdc1178c812cb205dc6f41d174a7b0f18fb93337e \
    --hash=sha256:6e4714cc64f474e4d6e37cfff31a814b509a35cb17de4fb1999907575684479c \
    --hash=sha256:72d8d3ef52c208ee1c7b2e341f7d71c6fd3157138abf1a95166e6165dd5d4369 \
    --hash=sha256:8ae6299f6c68de06f136f1f9e69458eae58f1dacf10af5c17353eae03aa0d827 \
    --hash=sha256:8b198cec6c72df5289c05b05b8b0969819783f9418e0409865dac47288d2a053 \
    --hash=sha256:99cd03ae7988a93dd00bcd9d0b75e1f6c426063d6f03d2f90b89e29b25b82dfa \
    --hash=sha256:9cf8022fb8d07a97c178b02327b284521c7708d7c71a9c9c355c178ac4bbd3d4 \
    --hash=sha256:9de2e279153a443c656f2defd67769e6d1e4163952b3c622dcea5b08a6405322 \
    --hash=sha256:9e93e79c2551ff263400e1e4be085a1210e12073a31c2011dbbda14bda0c6132 \
    --hash=sha256:9ff227395193126d82e60319a673a037d5de84633f11279e336f9c0f189ecc62 \
    --hash=sha256:a465da611f6fa124963b91bf432d960a555563efe4ed1cc403ba5077b15370aa \
    --hash=sha256:ad17025d226ee5beec591b52800c11680fca3df50b8b29fe51d882576e039ee0 \
    --hash=sha256:afb29c1ba2e5a3736f1c301d9d0abe3ec8b86957d04ddfa9d7a6a42b9367e396 \
    --hash=sha256:b85eb46a81787c50650f2392b9b4ef23e1f126313b9e0e9013b35c15e4288e2e \
    --hash=sha256:bb89f306e5da99f4d922728ddcd6f7fcebb3241fc40edebcb7284d7514741991 \
    --hash=sha256:cbde590d4faaa07c72bf979734738f328d239913ba3e043b1e98fe9a39f8b2b6 \
    --hash=sha256:cd2868886d547469123fadc46eac7ea5253ea7fcb139f12e1dfc2bbd406427d1 \
    --hash=sha256:d42b11d692e11b6634f7613ad8df5d6d5f8875f5d48939520d351007b3c13406 \
    --hash=sha256:f2d45f97ab6bb54753eab54fffe75aaf3de4ff2341c9daee1987ee1837636f1d \
    --hash=sha256:fd78e5fee591709f32ef6edb9a015b4aa1a5022598e36227500c8f4e02328d9c
pycparser==2.20 \
    --hash=sha256:2d475327684562c3a96cc71adf7dc8c4f0565175cf86b6d7a404ff4c771f15f0 \
    --hash=sha256:7582ad22678f0fcd81102833f60ef8d0e57288b6b5fb00323d101be910e35705
EOF

${PYPATH}/bin/pip install -r /tmp/requirements.txt

mkdir -p /tmp/wheels

${PYPATH}/bin/pip wheel -v /project -w /tmp/wheels --no-deps
wheel=$(ls /tmp/wheels/*.whl)

# Apply fixups.
auditwheel repair ${wheel} -w /project/dist
