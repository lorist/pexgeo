# pexgeo
Pexip Geo Location Policy server

Install an ubuntu AMI

```
sudo apt-get update
sudo apt-get install python-pip
sudo pip install virtualenv
git clone https://github.com/lorist/pexgeo.git
cd pexgeo
virtualenv policyvenv
source policyvenv/bin/activate
pip install -r requirements.txt
sudo add-apt-repository ppa:maxmind/ppa
sudo aptitude update
sudo aptitude install libmaxminddb0 libmaxminddb-dev mmdb-bin

```

