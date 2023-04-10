
To run tests, make sure nose and coverage are installed
and then run this from the top level package folder

% cd ~/reps/H5Gizmos
% nosetests --with-coverage --cover-html-dir=coverage --cover-xml --cover-package=H5Gizmos --cover-html

The coverage report will be in ./coverage/index.html

To run a specific test, for example:

% nosetests H5Gizmos/python/test/test_components.py:HeaderTest.test_header
