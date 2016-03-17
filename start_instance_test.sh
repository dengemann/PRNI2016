aws ec2 run-instances \
   --image-id ami-62474008 \
   --count 1 \
   --instance-type t2.micro \
   --key-name test-node-virginia \
   --user-data file://startup_tests3.sh \
   --instance-initiated-shutdown-behavior terminate \
   --iam-instance-profile Name=push-to-swish \
   --block-device-mapping file://block-device-mapping.json \
   --region us-east-1 \
   --security-groups launch-wizard-1 \
   --placement file://placement.json \
   # --dry-run
   # --ebs-optimized \
