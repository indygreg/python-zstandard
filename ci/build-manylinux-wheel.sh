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
cffi==1.11.5 \
    --hash=sha256:151b7eefd035c56b2b2e1eb9963c90c6302dc15fbd8c1c0a83a163ff2c7d7743 \
    --hash=sha256:1553d1e99f035ace1c0544050622b7bc963374a00c467edafac50ad7bd276aef \
    --hash=sha256:1b0493c091a1898f1136e3f4f991a784437fac3673780ff9de3bcf46c80b6b50 \
    --hash=sha256:2ba8a45822b7aee805ab49abfe7eec16b90587f7f26df20c71dd89e45a97076f \
    --hash=sha256:3c85641778460581c42924384f5e68076d724ceac0f267d66c757f7535069c93 \
    --hash=sha256:3eb6434197633b7748cea30bf0ba9f66727cdce45117a712b29a443943733257 \
    --hash=sha256:4c91af6e967c2015729d3e69c2e51d92f9898c330d6a851bf8f121236f3defd3 \
    --hash=sha256:770f3782b31f50b68627e22f91cb182c48c47c02eb405fd689472aa7b7aa16dc \
    --hash=sha256:79f9b6f7c46ae1f8ded75f68cf8ad50e5729ed4d590c74840471fc2823457d04 \
    --hash=sha256:7a33145e04d44ce95bcd71e522b478d282ad0eafaf34fe1ec5bbd73e662f22b6 \
    --hash=sha256:857959354ae3a6fa3da6651b966d13b0a8bed6bbc87a0de7b38a549db1d2a359 \
    --hash=sha256:87f37fe5130574ff76c17cab61e7d2538a16f843bb7bca8ebbc4b12de3078596 \
    --hash=sha256:95d5251e4b5ca00061f9d9f3d6fe537247e145a8524ae9fd30a2f8fbce993b5b \
    --hash=sha256:9d1d3e63a4afdc29bd76ce6aa9d58c771cd1599fbba8cf5057e7860b203710dd \
    --hash=sha256:a36c5c154f9d42ec176e6e620cb0dd275744aa1d804786a71ac37dc3661a5e95 \
    --hash=sha256:ae5e35a2c189d397b91034642cb0eab0e346f776ec2eb44a49a459e6615d6e2e \
    --hash=sha256:b0f7d4a3df8f06cf49f9f121bead236e328074de6449866515cea4907bbc63d6 \
    --hash=sha256:b75110fb114fa366b29a027d0c9be3709579602ae111ff61674d28c93606acca \
    --hash=sha256:ba5e697569f84b13640c9e193170e89c13c6244c24400fc57e88724ef610cd31 \
    --hash=sha256:be2a9b390f77fd7676d80bc3cdc4f8edb940d8c198ed2d8c0be1319018c778e1 \
    --hash=sha256:d5d8555d9bfc3f02385c1c37e9f998e2011f0db4f90e250e5bc0c0a85a813085 \
    --hash=sha256:e55e22ac0a30023426564b1059b035973ec82186ddddbac867078435801c7801 \
    --hash=sha256:e90f17980e6ab0f3c2f3730e56d1fe9bcba1891eeea58966e89d352492cc74f4 \
    --hash=sha256:ecbb7b01409e9b782df5ded849c178a0aa7c906cf8c5a67368047daab282b184 \
    --hash=sha256:ed01918d545a38998bfa5902c7c00e0fee90e957ce036a4000a88e3fe2264917 \
    --hash=sha256:edabd457cd23a02965166026fd9bfd196f4324fe6032e866d0f3bd0301cd486f \
    --hash=sha256:fdf1c1dc5bafc32bc5d08b054f94d659422b05aba244d6be4ddc1c72d9aa70fb
pycparser==2.18 \
    --hash=sha256:99a8ca03e29851d96616ad0404b4aad7d9ee16f25c9f9708a11faf2810f7b226
EOF

${PYPATH}/bin/pip install -r /tmp/requirements.txt

mkdir -p /tmp/wheels

${PYPATH}/bin/pip wheel -v /project -w /tmp/wheels --no-deps
wheel=$(ls /tmp/wheels/*.whl)

# Apply fixups.
auditwheel repair ${wheel} -w /output
