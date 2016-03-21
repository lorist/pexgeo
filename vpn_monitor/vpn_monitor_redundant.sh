#!/bin/sh
# This script will monitor another VPN instance and take over its routes
# if communication with the other instance fails
#yum -y install aws-cli

# VPN instance variables
# Other instance's IP to ping and route to grab if other node goes down
VPN_ID=<enter_main_vpn_instance_id>
VPN_RT_ID=<enter_your_route_id>

# My route to grab when I come back up
My_RT_ID=<usually_the_same_as_VPN_RT_ID>

# Public IP
PUBLIC_IP=<enter_your _elastic_ip>

# Specify the EC2 region that this will be running in (e.g. https://ec2.us-east-1.amazonaws.com)
EC2_URL=https://ec2.eu-central-1.amazonaws.com
EC2_REGION=`echo $EC2_URL | sed "s/https:\/\/ec2\.//g" | sed "s/\.amazonaws\.com//g"`

# Health Check variables
Num_Pings=3
Ping_Timeout=1
Wait_Between_Pings=2
Wait_for_Instance_Stop=60
Wait_for_Instance_Start=300

# Run aws-apitools-common.sh to set up default environment variables and to
# leverage AWS security credentials provided by EC2 roles
. /etc/profile.d/aws-apitools-common.sh

# Determine the VPN instance private IP so we can ping the other VPN instance, take over
# its route, and reboot it.  Requires EC2 DescribeInstances, ReplaceRoute, and Start/RebootInstances
# permissions.  The following example EC2 Roles policy will authorize these commands:
# {
#  "Statement": [
#    {
#      "Action": [
#        "ec2:DescribeInstances",
#        "ec2:CreateRoute",
#        "ec2:ReplaceRoute",
#        "ec2:StartInstances",
#        "ec2:StopInstances"
#      ],
#      "Effect": "Allow",
#      "Resource": "*"
#    }
#  ]
# }

# Get this instance's ID
Instance_ID=`/usr/bin/curl --silent http://169.254.169.254/latest/meta-data/instance-id`
# Get the other VPN instance's IP
# /opt/aws/bin/ec2-describe-instances i-cfc81072 -U https://ec2.eu-central-1.amazonaws.com | grep PRIVATEIPADDRESS -m 1 | awk '{print $2;}'
VPN_IP=`/opt/aws/bin/ec2-describe-instances $VPN_ID -U $EC2_URL | grep PRIVATEIPADDRESS -m 1 | awk '{print $2;}'`

echo `date` "-- Starting VPN monitor"

while [ . ]; do
  # Check health of other VPN instance
  pingresult=`ping -c $Num_Pings -W $Ping_Timeout $VPN_IP | grep time= | wc -l`
  # Check to see if any of the health checks succeeded, if not
  if [ "$pingresult" == "0" ]; then
    # Set HEALTHY variables to unhealthy (0)
    ROUTE_HEALTHY=0
    VPN_HEALTHY=0
    STOPPING_VPN=1
    while [ "$VPN_HEALTHY" == "0" ]; do
      # VPN instance is unhealthy, loop while we try to fix it
      if [ "$ROUTE_HEALTHY" == "0" ]; then
    	echo `date` "-- Other VPN heartbeat failed, taking over $VPN_RT_ID default route"
    	/opt/aws/bin/ec2-replace-route $My_RT_ID -r 172.31.0.0/16 -i $Instance_ID -U $EC2_URL
      /opt/aws/bin/ec2-replace-route $My_RT_ID -r 172.32.0.0/16 -i $Instance_ID -U $EC2_URL
      /opt/aws/bin/ec2-replace-route $My_RT_ID -r 172.33.0.0/16 -i $Instance_ID -U $EC2_URL
      /opt/aws/bin/ec2-replace-route $My_RT_ID -r 172.34.0.0/16 -i $Instance_ID -U $EC2_URL
      echo `date` "-- Adding Public IP $PUBLIC_IP instance to this instance"
      /opt/aws/bin/ec2-associate-address --region $EC2_REGION $PUBLIC_IP -i $Instance_ID
      echo `date` "-- Starting IPSEC"
      service ipsec start

	    ROUTE_HEALTHY=1
      fi
      # Check VPN state to see if we should stop it or start it again
      # The line below works with EC2 API tools version 1.6.12.2 2013-10-15. If you are using a different version and your script is stuck at VPN_STATE, please modify the script to "print $5;" instead of "print $4;".
      #VPN_STATE=`/opt/aws/bin/ec2-describe-instances $VPN_ID -U $EC2_URL | grep INSTANCE | awk '{print $4;}'`
      # The line below replaces the EC2 API tools with the AWS CLI to improve stability across EC2 API tool versions
      # VPN_STATE=`aws ec2 describe-instances --instance-ids i-cfc81072 --region eu-central-1 --output text --query 'Reservations[*].Instances[*].State.Name'`

      VPN_STATE=`aws ec2 describe-instances --instance-ids $VPN_ID --region $EC2_REGION --output text --query 'Reservations[*].Instances[*].State.Name'`

      if [ "$VPN_STATE" == "stopped" ]; then
    	echo `date` "-- Other VPN instance stopped, starting it back up"
        /opt/aws/bin/ec2-start-instances $VPN_ID -U $EC2_URL
	      VPN_HEALTHY=1
        sleep $Wait_for_Instance_Start
      else
	    # if [ "$STOPPING_VPN" == "0" ]; then
    	#   echo `date` "-- Other VPN instance $VPN_STATE, attempting to stop for reboot"
	    #   /opt/aws/bin/ec2-stop-instances $VPN_ID -U $EC2_URL
	    #   STOPPING_VPN=1
	    # fi
     #    sleep $Wait_for_Instance_Stop
      fi
    done
  else
    sleep $Wait_Between_Pings
  fi
done
