from aws_cdk.aws_s3_assets import Asset as S3asset

import os.path

from aws_cdk import (
    
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_rds as rds,
    aws_elasticloadbalancingv2 as elbv2,
    CfnOutput,
    CfnParameter
)

from constructs import Construct

class Assignment6AlbStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
    
        
        #defining my input parameters
        instance_type = CfnParameter(self, "instanceType", type="ec2.InstanceType", allowed_values = ["t2.micro", "t2.small"], description="The instance type you want to use", default = "t2.micro").value_as_string
        key_pair_name = CfnParameter(self, "keyPairName", type="String", description="Your key name pair").value_as_string
        your_ip_cidr = CfnParameter(self, "yourIpCidr", type="String", description="Your IP CIDR").value_as_string
        
        
        #Creating subnets
        publicSubnet1 = ec2.SubnetConfiguration(name="PublicSubnet01",subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24,
                                                reserved=False)

        publicSubnet2 = ec2.SubnetConfiguration(name="PublicSubnet02",subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24,
                                                reserved = False)
        
        # Creating a VPC
        EngineeringVPC= ec2.Vpc(self, "EngineeringVPC", 
                            cidr= "10.0.0.0/18",
                            subnet_configuration=[publicSubnet1, publicSubnet2])
                            
                            
        
        #Creating security group
        
        web_servers_sg = ec2.SecurityGroup(self, "WebserversSG",vpc = EngineeringVPC, allow_all_outbound = True)
        
        web_servers_sg.add_ingress_rule(ec2.Peer.ipv4(your_ip_cidr), ec2.Port.tcp(22), "Allow SSH traffic")
        web_servers_sg.add_egress_rule(ec2.Peer.ipv4("0.0.0.0/0"), ec2.Port.tcp(80),"Allow HTTP traffic")
        
                            
        # Instance Role and SSM Managed Policy
        InstanceRole = iam.Role(self, "InstanceSSM", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))

        InstanceRole.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))
        
        user_data = ec2.UserData.for_linux()
        user_data.add_commands("""#!/bin/bash
                                    yum update -y
                                    yum install -y git httpd php
                                    service httpd start
                                    chkconfig httpd on
                                    aws s3 cp s3://seis665-public/index.php /var/www/html/""")

        
        # Creating EC2 instances
        cdk_web_instance1 = ec2.Instance(self, "cdk_web_instance",
                                            instance_type=ec2.InstanceType(instance_type),
                                            machine_image=ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2),
                                            role=InstanceRole,
                                            key_pair = key_pair_name,
                                            vpc=EngineeringVPC,
                                            vpc_subnets={"subnet_group_name": "PublicSubnet01"},
                                            user_data=user_data)
        
        cdk_web_instance2 = ec2.Instance(self, "cdk_web_instance2",
                                            instance_type=ec2.InstanceType(instance_type),
                                            machine_image=ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2),
                                            role=InstanceRole,
                                            key_pair = key_pair_name,
                                            vpc=EngineeringVPC,
                                            vpc_subnets={"subnet_group_name": "PublicSubnet02"},
                                            user_data=user_data)                                 
                       
        
        # Creating ALB
        
        EngineeringWebservers = elbv2.ApplicationLoadBalancer(self, "EngineeringLB", vpc = EngineeringVPC, internet_facing = True)
        
        
        
        #Creating target group
        
        target_group = elbv2.ApplicationTargetGroup(self, "EngineeringWebServer", 
                                                    port = 80,
                                                    vpc = EngineeringVPC,
                                                    targets = [cdk_web_instance1.instance_id, cdk_web_instance2.instance_id],
                                                    health_check = {"path": "/",
                                                                    "port": "80"})
        
        
        
        #Adding listener to the load balancer
        listener = EngineeringWebservers.add_listener("Listener",
                    port = 80,
                    default_target_groups=[target_group])
                    
                    
                    
        #Output Load balancer DNS name
        CfnOutput(self, "WebUrl", value = EngineeringWebservers.load_balancer_dns_name)
            