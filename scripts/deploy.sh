#!/bin/bash

# Quick deployment wrapper for FullTokenContract
# This script provides a simple interface to deploy_token.py

set -e

# Default values
NAME="ProvableGameToken"
SYMBOL="PGT"
BASE_URI="https://api.provable.games/token/"
ROYALTY_RECEIVER="0x127fd5f1fe78a71f8bcd1fec63e3fe2f0486b6ecd5c86a0466c3a21fa5cfcec"
ROYALTY_FRACTION=500
GAME_REGISTRY="0x00348dafbd271cc82bfc57e3edd3a7b3163008f53c586e31d822862b72e1a663"
SALT=2
PROFILE="default"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}FullTokenContract Quick Deploy${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            NAME="$2"
            shift 2
            ;;
        --symbol)
            SYMBOL="$2"
            shift 2
            ;;
        --base-uri)
            BASE_URI="$2"
            shift 2
            ;;
        --salt)
            SALT="$2"
            shift 2
            ;;
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --name NAME           Token name (default: ProvableGameToken)"
            echo "  --symbol SYMBOL       Token symbol (default: PGT)"
            echo "  --base-uri URI        Base URI (default: https://api.provable.games/token/)"
            echo "  --salt NUMBER         Salt for deployment (default: 0)"
            echo "  --profile PROFILE     sncast profile (default: default)"
            echo "  --help, -h            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Deploy with defaults"
            echo "  $0 --name MyToken --symbol MTK       # Deploy custom token"
            echo "  $0 --salt 1                           # Deploy with salt=1"
            echo ""
            echo "For advanced options, use scripts/deploy_token.py directly"
            exit 0
            ;;
        *)
            echo -e "${YELLOW}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Display configuration
echo -e "${GREEN}Configuration:${NC}"
echo "  Name: $NAME"
echo "  Symbol: $SYMBOL"
echo "  Base URI: $BASE_URI"
echo "  Salt: $SALT"
echo "  Profile: $PROFILE"
echo ""

# Run Python deployment script
python3 scripts/deploy_token.py \
    --name "$NAME" \
    --symbol "$SYMBOL" \
    --base-uri "$BASE_URI" \
    --royalty-receiver "$ROYALTY_RECEIVER" \
    --royalty-fraction "$ROYALTY_FRACTION" \
    --game-registry "$GAME_REGISTRY" \
    --salt "$SALT" \
    --profile "$PROFILE"

# Check if deployment was successful
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    echo ""

    # Display latest deployment info if available
    if [ -f "LATEST_DEPLOYMENT.txt" ]; then
        echo -e "${BLUE}Latest Deployment Details:${NC}"
        cat LATEST_DEPLOYMENT.txt
    fi
else
    echo ""
    echo -e "${YELLOW}⚠️  Deployment encountered an error${NC}"
    exit 1
fi
