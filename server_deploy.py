import subprocess

cmd = 'cd setuptools-18.4;python setup.py install --user'
p = subprocess.Popen(cmd, shell=True)
p.wait()

cmd = 'cd Beaker-1.7.0;python setup.py install --user'
p = subprocess.Popen(cmd, shell=True)
p.wait()

cmd = 'cd bottle-0.12.7;python setup.py install --user'
p = subprocess.Popen(cmd, shell=True)
p.wait()

cmd = 'sudo apt-get update'
p = subprocess.Popen(cmd, shell=True)
p.wait()

cmd = 'sudo apt-get -y install python-pip'
p = subprocess.Popen(cmd, shell=True)
p.wait()

cmd = 'sudo pip install BeautifulSoup4'
p = subprocess.Popen(cmd, shell=True)
p.wait()

cmd = 'sudo apt-get install python-httplib2'
p = subprocess.Popen(cmd, shell=True)
p.wait()

cmd = "tmux new -d -s my-session 'python FrontEnd.py'"
p = subprocess.Popen(cmd, shell=True)
p.wait()


