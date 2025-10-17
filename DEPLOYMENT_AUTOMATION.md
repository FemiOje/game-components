# Automated Deployment for FullTokenContract

## Quick Start

Deploy a new FullTokenContract with a single command:

```bash
cd /workspace/game-components
./scripts/deploy.sh
```

That's it! The script will:
- ✅ Handle ByteArray serialization automatically
- ✅ Deploy via UDC using sncast (Katana v0.9.0-rc.2 compatible)
- ✅ Extract and display the contract address
- ✅ Verify the deployment
- ✅ Save details to `LATEST_DEPLOYMENT.txt`

## Why These Scripts?

The standard deployment tools (starkli deploy, sncast deploy) don't work with Katana v0.9.0-rc.2:
- **starkli v0.4.2**: `BlockIdDe` deserialization error prevents transaction submission
- **sncast deploy**: Uses hardcoded UDC address that doesn't exist on custom networks

**Our solution**: Direct UDC invocation via sncast with proper ByteArray serialization.

## Usage Examples

### Example 1: Default Deployment

```bash
./scripts/deploy.sh
```

Deploys "ProvableGameToken" (PGT) with default configuration.

**Output:**
```
🎉 Contract deployed successfully!
   Contract Address: 0x3d3d11cc1dc5a92a70fd520e0292d476453024b1cbf913585d4d97f5355c160
✅ Verification successful!
```

### Example 2: Custom Token

```bash
./scripts/deploy.sh --name "MyGameToken" --symbol "MGT"
```

Deploys a custom token with your specified name and symbol.

### Example 3: Multiple Deployments

```bash
./scripts/deploy.sh --salt 1 --name "Token1" --symbol "TK1"
./scripts/deploy.sh --salt 2 --name "Token2" --symbol "TK2"
./scripts/deploy.sh --salt 3 --name "Token3" --symbol "TK3"
```

Deploy multiple instances by using different salt values.

### Example 4: Advanced Configuration

For full control over all parameters:

```bash
python3 scripts/deploy_token.py \
  --name "AdvancedToken" \
  --symbol "ADV" \
  --base-uri "https://api.example.com/tokens/" \
  --royalty-fraction 750 \
  --game-registry "0xYOUR_REGISTRY" \
  --event-relayer "0xYOUR_RELAYER" \
  --salt 1
```

## Available Scripts

### 1. `deploy.sh` - Quick Deploy (Recommended)

**Purpose**: Simple interface for common deployments

**Usage:**
```bash
./scripts/deploy.sh [OPTIONS]
```

**Options:**
- `--name NAME` - Token name
- `--symbol SYMBOL` - Token symbol
- `--base-uri URI` - Metadata base URI
- `--salt NUMBER` - Deployment salt
- `--profile PROFILE` - sncast profile
- `--help` - Show help

### 2. `deploy_token.py` - Full-Featured Script

**Purpose**: Complete control over all deployment parameters

**Usage:**
```bash
python3 scripts/deploy_token.py [OPTIONS]
```

**All Options:**
- Core: `--name`, `--symbol`, `--base-uri`
- Royalties: `--royalty-receiver`, `--royalty-fraction`
- Optional: `--game-registry`, `--event-relayer`
- Contract: `--class-hash`, `--udc-address`
- Deployment: `--salt`, `--no-unique`, `--no-verify`
- Network: `--profile`

**See full documentation:** `scripts/README.md`

## What Gets Deployed

### Constructor Parameters

The FullTokenContract is deployed with these parameters:

```cairo
constructor(
    name: ByteArray,                          // "ProvableGameToken"
    symbol: ByteArray,                        // "PGT"
    base_uri: ByteArray,                      // "https://api.provable.games/token/"
    royalty_receiver: ContractAddress,        // Your deployer address
    royalty_fraction: u128,                   // 500 (5%)
    game_registry_address: Option<ContractAddress>,  // Registry address or None
    event_relayer_address: Option<ContractAddress>,  // Relayer address or None
)
```

### Default Configuration

| Parameter | Default Value |
|-----------|---------------|
| Name | ProvableGameToken |
| Symbol | PGT |
| Base URI | https://api.provable.games/token/ |
| Royalty Receiver | 0x127fd5f1fe78a71f8bcd1fec63e3fe2f0486b6ecd5c86a0466c3a21fa5cfcec |
| Royalty Fraction | 500 (5%) |
| Game Registry | 0x00348dafbd271cc82bfc57e3edd3a7b3163008f53c586e31d822862b72e1a663 |
| Event Relayer | None |
| Class Hash | 0x075137b5c45312610d7cb6d43982e5fd5bd0df6c0b1e51518ced64a91f125e85 |
| UDC Address | 0x041a78e741e5af2fec34b695679bc6891742439f7afb8484ecd7766661ad02bf |

## Output Files

### LATEST_DEPLOYMENT.txt

Contains details of the most recent deployment:

```
Contract Address: 0x3d3d11cc1dc5a92a70fd520e0292d476453024b1cbf913585d4d97f5355c160
Transaction Hash: 0x03e236d3215dce3cb74eb5d637eec669f52dc1443d8b6797c1ae5b30b471a964
Class Hash: 0x075137b5c45312610d7cb6d43982e5fd5bd0df6c0b1e51518ced64a91f125e85
Name: ProvableGameToken
Symbol: PGT
```

**Access deployed address:**
```bash
cat LATEST_DEPLOYMENT.txt | grep "Contract Address"
```

## Technical Details

### How It Works

1. **ByteArray Serialization**: Converts strings to Cairo ByteArray format
   - Format: `[num_full_words, word1, ..., pending_word, pending_len]`
   - Each full word = 31 bytes
   - Pending word = remaining bytes < 31 bytes

2. **UDC Invocation**: Calls `deployContract` on Universal Deployer Contract
   - Uses sncast (compatible with Katana v0.9.0-rc.2)
   - Passes serialized constructor arguments
   - Returns transaction hash

3. **Address Extraction**: Parses transaction receipt
   - Reads UDC `ContractDeployed` event
   - Extracts contract address from event data
   - Verifies by calling `name()` function

4. **Verification**: Confirms deployment success
   - Calls contract's `name()` function
   - Compares with expected value
   - Reports success or failure

### ByteArray Format Example

**String:** "ProvableGameToken" (17 bytes)

**Serialization:**
```
0                              # num_full_words = 0 (17 < 31)
0x50726f7661626c6547616d65546f6b656e  # pending_word (17 bytes)
17                             # pending_len
```

**String:** "https://api.provable.games/token/" (33 bytes)

**Serialization:**
```
1                              # num_full_words = 1 (33 / 31 = 1 R 2)
0x68747470733a2f2f6170692e70726f7661626c652e67616d65732f746f6b65  # full word (31 bytes)
0x6e2f                         # pending_word (2 bytes)
2                              # pending_len
```

## Prerequisites

### Required

1. **sncast v0.50.0+**
   ```bash
   sncast --version
   ```
   Install: `snfoundryup`

2. **Python 3.8+**
   ```bash
   python3 --version
   ```

3. **snfoundry.toml Configuration**
   - Location: `packages/token/snfoundry.toml`
   - Must contain account details and RPC URL

### Optional

- **starkli** (for transaction queries)
  ```bash
  starkli --version
  ```
  Install: `starkliup`

## Troubleshooting

### Problem: "sncast: command not found"

**Solution:**
```bash
curl -L https://raw.githubusercontent.com/foundry-rs/starknet-foundry/master/scripts/install.sh | sh
snfoundryup
```

### Problem: "Account not found"

**Solution:** Check snfoundry.toml configuration:
```bash
cat packages/token/snfoundry.toml
```

Ensure account details are correct.

### Problem: Contract address not extracted

**Solution:** Script provides manual instructions. Run:
```bash
export STARKNET_RPC="https://api.cartridge.gg/x/provable-dw/katana"
starkli transaction-receipt 0xYOUR_TX_HASH
```

Address is in `events[0].data[0]`.

### Problem: Insufficient balance

**Solution:** Fund your deployer account with ETH or STRK.

## Advanced Usage

### Custom Class Hash (After Modifications)

1. Modify contract code
2. Build: `cd packages/token && scarb build`
3. Declare: (use compatible tool for your network)
4. Deploy: `python3 scripts/deploy_token.py --class-hash 0xNEW_HASH`

### Different Networks

Add profiles to `snfoundry.toml`:

```toml
[sncast.mainnet]
url = "https://starknet-mainnet.public.blastapi.io"
account = "mainnet-deployer"
```

Deploy:
```bash
./scripts/deploy.sh --profile mainnet
```

### Programmatic Integration

```python
from scripts.deploy_token import DeploymentConfig, deploy_via_udc

config = DeploymentConfig(
    name="MyToken",
    symbol="MTK",
    # ... other params
)

success, tx_hash, error = deploy_via_udc(config)
```

## Testing the Scripts

Deployed instances for testing:

| Salt | Name | Symbol | Address |
|------|------|--------|---------|
| 0 | ProvableGameToken | PGT | 0x3d3d11cc1dc5a92a70fd520e0292d476453024b1cbf913585d4d97f5355c160 |
| 1 | ProvableGameToken | PGT | 0x5fa36351bc140fc186a539391e056b5e5b7f5766819672324b2eb48492c5212 |
| 2 | TestToken | TEST | 0x373a4dd6510c1ca9763b4b372909d37e63471b02188e6ec972868d5b07491a4 |

All verified and working on Provable Katana network.

## Documentation

- **Full Script Documentation**: `scripts/README.md`
- **Successful Deployment Example**: `DEPLOYMENT_SUCCESS.md`
- **Version Compatibility Issues**: `DEPLOYMENT_READY.md`
- **Contract Source**: `packages/token/src/examples/full_token_contract.cairo`

## Key Achievements

✅ **Automated ByteArray serialization** - No manual hex conversion needed

✅ **Katana v0.9.0-rc.2 compatible** - Works where starkli fails

✅ **Automatic verification** - Confirms deployment success

✅ **User-friendly interface** - Simple bash wrapper for common cases

✅ **Full control available** - Python script for advanced scenarios

✅ **Comprehensive documentation** - Multiple guides and examples

✅ **Battle-tested** - Multiple successful deployments verified

## Quick Reference

```bash
# Simple deployment
./scripts/deploy.sh

# Custom token
./scripts/deploy.sh --name MyToken --symbol MTK

# Multiple instances
./scripts/deploy.sh --salt 1
./scripts/deploy.sh --salt 2

# Advanced options
python3 scripts/deploy_token.py --help

# Check latest deployment
cat LATEST_DEPLOYMENT.txt

# Verify deployment
sncast call \
  --contract-address $(grep "Contract Address" LATEST_DEPLOYMENT.txt | cut -d' ' -f3) \
  --function name
```

## Support

For issues or questions:
1. Review `scripts/README.md` for detailed documentation
2. Check `DEPLOYMENT_SUCCESS.md` for working example
3. Examine script source code for implementation details

---

**Ready to deploy?** Run `./scripts/deploy.sh` now!
