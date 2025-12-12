#!/bin/bash
# Bash deployment script for Twilio Stream Infrastructure

set -e

echo "========================================"
echo "  Twilio Stream Deployment Script"
echo "========================================"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI is not installed or not in PATH"
    exit 1
fi
echo "AWS CLI: $(aws --version)"

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "CDK not found. Installing AWS CDK..."
    npm install -g aws-cdk
fi
echo "CDK Version: $(cdk --version)"

# Navigate to infrastructure directory
cd infrastructure

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Bootstrap CDK (if needed)
echo ""
echo "Checking CDK bootstrap status..."
cdk bootstrap

# Synthesize the stack
echo ""
echo "Synthesizing CloudFormation template..."
cdk synth

# Deploy
echo ""
echo "Deploying stack..."
cdk deploy --require-approval never

echo ""
echo "========================================"
echo "  Deployment Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Copy the TwiML Webhook URL from the output above"
echo "2. Go to Twilio Console -> Phone Numbers -> Your +1 number"
echo "3. Set the 'When a call comes in' webhook to the TwiML URL"
echo "4. Make a test call to your Twilio number!"


