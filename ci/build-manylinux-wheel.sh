#!/usr/bin/env bash
# Copyright (c) 2018-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

set -ex

if [ -e /tmp/wheels ]; then
    echo "/tmp/wheels should not exist!"
    exit 1
fi

cat > /tmp/requirements.txt << EOF
cffi==1.13.2 \
    --hash=sha256:0b49274afc941c626b605fb59b59c3485c17dc776dc3cc7cc14aca74cc19cc42 \
    --hash=sha256:0e3ea92942cb1168e38c05c1d56b0527ce31f1a370f6117f1d490b8dcd6b3a04 \
    --hash=sha256:135f69aecbf4517d5b3d6429207b2dff49c876be724ac0c8bf8e1ea99df3d7e5 \
    --hash=sha256:19db0cdd6e516f13329cba4903368bff9bb5a9331d3410b1b448daaadc495e54 \
    --hash=sha256:2781e9ad0e9d47173c0093321bb5435a9dfae0ed6a762aabafa13108f5f7b2ba \
    --hash=sha256:291f7c42e21d72144bb1c1b2e825ec60f46d0a7468f5346841860454c7aa8f57 \
    --hash=sha256:2c5e309ec482556397cb21ede0350c5e82f0eb2621de04b2633588d118da4396 \
    --hash=sha256:2e9c80a8c3344a92cb04661115898a9129c074f7ab82011ef4b612f645939f12 \
    --hash=sha256:32a262e2b90ffcfdd97c7a5e24a6012a43c61f1f5a57789ad80af1d26c6acd97 \
    --hash=sha256:3c9fff570f13480b201e9ab69453108f6d98244a7f495e91b6c654a47486ba43 \
    --hash=sha256:415bdc7ca8c1c634a6d7163d43fb0ea885a07e9618a64bda407e04b04333b7db \
    --hash=sha256:42194f54c11abc8583417a7cf4eaff544ce0de8187abaf5d29029c91b1725ad3 \
    --hash=sha256:4424e42199e86b21fc4db83bd76909a6fc2a2aefb352cb5414833c030f6ed71b \
    --hash=sha256:4a43c91840bda5f55249413037b7a9b79c90b1184ed504883b72c4df70778579 \
    --hash=sha256:599a1e8ff057ac530c9ad1778293c665cb81a791421f46922d80a86473c13346 \
    --hash=sha256:5c4fae4e9cdd18c82ba3a134be256e98dc0596af1e7285a3d2602c97dcfa5159 \
    --hash=sha256:5ecfa867dea6fabe2a58f03ac9186ea64da1386af2159196da51c4904e11d652 \
    --hash=sha256:62f2578358d3a92e4ab2d830cd1c2049c9c0d0e6d3c58322993cc341bdeac22e \
    --hash=sha256:6471a82d5abea994e38d2c2abc77164b4f7fbaaf80261cb98394d5793f11b12a \
    --hash=sha256:6d4f18483d040e18546108eb13b1dfa1000a089bcf8529e30346116ea6240506 \
    --hash=sha256:71a608532ab3bd26223c8d841dde43f3516aa5d2bf37b50ac410bb5e99053e8f \
    --hash=sha256:74a1d8c85fb6ff0b30fbfa8ad0ac23cd601a138f7509dc617ebc65ef305bb98d \
    --hash=sha256:7b93a885bb13073afb0aa73ad82059a4c41f4b7d8eb8368980448b52d4c7dc2c \
    --hash=sha256:7d4751da932caaec419d514eaa4215eaf14b612cff66398dd51129ac22680b20 \
    --hash=sha256:7f627141a26b551bdebbc4855c1157feeef18241b4b8366ed22a5c7d672ef858 \
    --hash=sha256:8169cf44dd8f9071b2b9248c35fc35e8677451c52f795daa2bb4643f32a540bc \
    --hash=sha256:aa00d66c0fab27373ae44ae26a66a9e43ff2a678bf63a9c7c1a9a4d61172827a \
    --hash=sha256:ccb032fda0873254380aa2bfad2582aedc2959186cce61e3a17abc1a55ff89c3 \
    --hash=sha256:d754f39e0d1603b5b24a7f8484b22d2904fa551fe865fd0d4c3332f078d20d4e \
    --hash=sha256:d75c461e20e29afc0aee7172a0950157c704ff0dd51613506bd7d82b718e7410 \
    --hash=sha256:dcd65317dd15bc0451f3e01c80da2216a31916bdcffd6221ca1202d96584aa25 \
    --hash=sha256:e570d3ab32e2c2861c4ebe6ffcad6a8abf9347432a37608fe1fbd157b3f0036b \
    --hash=sha256:fd43a88e045cf992ed09fa724b5315b790525f2676883a6ea64e3263bae6549d
pycparser==2.19 \
    --hash=sha256:a988718abfad80b6b157acce7bf130a30876d27603738ac39f140993246b25b3
EOF

${PYPATH}/bin/pip install -r /tmp/requirements.txt

mkdir -p /tmp/wheels

${PYPATH}/bin/pip wheel -v /project -w /tmp/wheels --no-deps
wheel=$(ls /tmp/wheels/*.whl)

# Apply fixups.
auditwheel repair ${wheel} -w /project/dist
