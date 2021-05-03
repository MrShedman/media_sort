from setuptools import setup, find_packages

setup(name="media_sort",
      version="0.0.1",
      description="Image and video file sorter",
      author='Ross Cunningham',
      author_email="roscoacer@googlemail.com",
      url="https://github.com/MrShedman/media_sort",
      packages=find_packages(),
      install_requires=["Pillow", "filetype", "hachoir", "exifread"])