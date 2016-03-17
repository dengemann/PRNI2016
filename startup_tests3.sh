#!/bin/bash

echo "updating code ..."
source /home/ubuntu/.bashrc
source /home/ubuntu/miniconda2/bin/activate swish
/home/ubuntu/miniconda2/bin/pip install boto
cd (/home/ubuntu/github/PRNI2016 \
    && git pull origin master \
    && echo "updating code ... done" \
    && python compute_test_s3.py --subject ubuntu-test-s3)
sudo poweroff