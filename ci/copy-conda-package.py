import os
import platform
import shutil

if platform.system() == "Linux":
    build_dir = "/usr/share/miniconda/conda-bld"
elif platform.system() == "Windows":
    build_dir = "C:/Miniconda/conda-bld"
else:
    raise Exception("Unsupported platform: %s", platform.system())

dest_dir = "dist"

if not os.path.exists(dest_dir):
    os.mkdir(dest_dir)

print("scanning %s for packages" % build_dir)
for root, _, files in os.walk(build_dir):
    for f in files:
        source = os.path.join(root, f)
        if not source.endswith(".conda"):
            continue

        print("copying %s" % source)
        shutil.copyfile(source, os.path.join(dest_dir, f))
