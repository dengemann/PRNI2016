#!/bin/bash
echo updating code ...
source activate swish
cd github/PRNI2016
git pull origin master
echo updating code ... done

echo making swap file ...
sudo chown ubuntu /mnt
sudo dd if=/dev/zero of=/mnt/swapfile bs=1M count=16384
sudo chown root:root /mnt/swapfile
sudo chmod 600 /mnt/swapfile
sudo mkswap /mnt/swapfile
sudo swapon /mnt/swapfile
echo "/mnt/swapfile swap swap defaults 0 0" | sudo tee -a /etc/fstab
sudo swapon -a
echo making swap file ... done
