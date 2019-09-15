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
cffi==1.12.3 \
    --hash=sha256:041c81822e9f84b1d9c401182e174996f0bae9991f33725d059b771744290774 \
    --hash=sha256:046ef9a22f5d3eed06334d01b1e836977eeef500d9b78e9ef693f9380ad0b83d \
    --hash=sha256:066bc4c7895c91812eff46f4b1c285220947d4aa46fa0a2651ff85f2afae9c90 \
    --hash=sha256:066c7ff148ae33040c01058662d6752fd73fbc8e64787229ea8498c7d7f4041b \
    --hash=sha256:2444d0c61f03dcd26dbf7600cf64354376ee579acad77aef459e34efcb438c63 \
    --hash=sha256:300832850b8f7967e278870c5d51e3819b9aad8f0a2c8dbe39ab11f119237f45 \
    --hash=sha256:34c77afe85b6b9e967bd8154e3855e847b70ca42043db6ad17f26899a3df1b25 \
    --hash=sha256:46de5fa00f7ac09f020729148ff632819649b3e05a007d286242c4882f7b1dc3 \
    --hash=sha256:4aa8ee7ba27c472d429b980c51e714a24f47ca296d53f4d7868075b175866f4b \
    --hash=sha256:4d0004eb4351e35ed950c14c11e734182591465a33e960a4ab5e8d4f04d72647 \
    --hash=sha256:4e3d3f31a1e202b0f5a35ba3bc4eb41e2fc2b11c1eff38b362de710bcffb5016 \
    --hash=sha256:50bec6d35e6b1aaeb17f7c4e2b9374ebf95a8975d57863546fa83e8d31bdb8c4 \
    --hash=sha256:55cad9a6df1e2a1d62063f79d0881a414a906a6962bc160ac968cc03ed3efcfb \
    --hash=sha256:5662ad4e4e84f1eaa8efce5da695c5d2e229c563f9d5ce5b0113f71321bcf753 \
    --hash=sha256:59b4dc008f98fc6ee2bb4fd7fc786a8d70000d058c2bbe2698275bc53a8d3fa7 \
    --hash=sha256:73e1ffefe05e4ccd7bcea61af76f36077b914f92b76f95ccf00b0c1b9186f3f9 \
    --hash=sha256:a1f0fd46eba2d71ce1589f7e50a9e2ffaeb739fb2c11e8192aa2b45d5f6cc41f \
    --hash=sha256:a2e85dc204556657661051ff4bab75a84e968669765c8a2cd425918699c3d0e8 \
    --hash=sha256:a5457d47dfff24882a21492e5815f891c0ca35fefae8aa742c6c263dac16ef1f \
    --hash=sha256:a8dccd61d52a8dae4a825cdbb7735da530179fea472903eb871a5513b5abbfdc \
    --hash=sha256:ae61af521ed676cf16ae94f30fe202781a38d7178b6b4ab622e4eec8cefaff42 \
    --hash=sha256:b012a5edb48288f77a63dba0840c92d0504aa215612da4541b7b42d849bc83a3 \
    --hash=sha256:d2c5cfa536227f57f97c92ac30c8109688ace8fa4ac086d19d0af47d134e2909 \
    --hash=sha256:d42b5796e20aacc9d15e66befb7a345454eef794fdb0737d1af593447c6c8f45 \
    --hash=sha256:dee54f5d30d775f525894d67b1495625dd9322945e7fee00731952e0368ff42d \
    --hash=sha256:e070535507bd6aa07124258171be2ee8dfc19119c28ca94c9dfb7efd23564512 \
    --hash=sha256:e1ff2748c84d97b065cc95429814cdba39bcbd77c9c85c89344b317dc0d9cbff \
    --hash=sha256:ed851c75d1e0e043cbf5ca9a8e1b13c4c90f3fbd863dacb01c0808e2b5204201
pycparser==2.19 \
    --hash=sha256:a988718abfad80b6b157acce7bf130a30876d27603738ac39f140993246b25b3
EOF

${PYPATH}/bin/pip install -r /tmp/requirements.txt

mkdir -p /tmp/wheels

${PYPATH}/bin/pip wheel -v /project -w /tmp/wheels --no-deps
wheel=$(ls /tmp/wheels/*.whl)

# Apply fixups.
auditwheel repair ${wheel} -w /project/dist
