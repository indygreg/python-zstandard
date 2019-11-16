import os
import shutil
from conda_build.config import Config

build_dir = Config().bldpkgs_dir
dest_dir = "dist"

if not os.path.exists(dest_dir):
    os.mkdir(dest_dir)

print("scanning %s for packages" % build_dir)
for p in os.listdir(build_dir):
    if not p.endswith(".tar.bz2"):
        continue

    source = os.path.join(build_dir, p)
    print("copying %s" % source)
    shutil.copyfile(source, os.path.join(dest_dir, p))
