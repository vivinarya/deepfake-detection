#!/usr/bin/env python3
import aws_cdk as cdk
from safeguard_stack import SafeGuardStack

app = cdk.App()
SafeGuardStack(
    app, "SafeGuardStack",
    env=cdk.Environment(region="ap-south-1")
)
app.synth()