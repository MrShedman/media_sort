from setuptools import setup, find_packages

setup(name="image_sort",
      version="0.0.1",
      description="Image and video file sorter",
      author='Ross Cunningham',
      packages=find_packages(),
      install_requires=["Pillow", "filetype", "hachoir", "exifread"])