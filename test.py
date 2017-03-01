import nose
from os import path

file_path = path.abspath(__file__)
tests_path = path.join(path.abspath(path.dirname(file_path)), "tests")
nose.main(argv=[path.abspath(__file__), "--with-coverage", "--cover-erase", "--cover-package=frapalyzer", tests_path])
