#!/usr/bin/env python3
"""
Automated deployment script for FullTokenContract on Starknet/Katana.

This script handles:
- Proper ByteArray serialization for string parameters
- Direct UDC invocation via sncast (compatible with Katana v0.9.0-rc.2)
- Automatic extraction of deployed contract address
- Error handling and validation

Usage:
    python3 scripts/deploy_token.py [options]

Requirements:
    - sncast v0.50.0 or later
    - snfoundry.toml configured with account details
"""

import json
import subprocess
import sys
import argparse
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DeploymentConfig:
    """Configuration for token deployment."""
    name: str
    symbol: str
    base_uri: str
    royalty_receiver: str
    royalty_fraction: int
    game_registry_address: Optional[str]
    event_relayer_address: Optional[str]
    class_hash: str
    udc_address: str
    profile: str
    salt: int = 0
    unique: bool = True


def encode_bytearray(s: str) -> List[str]:
    """
    Encode a string into Cairo ByteArray format.

    ByteArray format: [num_full_words, word1, word2, ..., pending_word, pending_word_len]
    - Each full word is 31 bytes
    - Pending word contains remaining bytes (< 31)
    - Pending len is the number of bytes in pending word

    Args:
        s: String to encode

    Returns:
        List of hex strings representing the ByteArray
    """
    s_bytes = s.encode('utf-8')
    num_full_words = len(s_bytes) // 31
    pending_len = len(s_bytes) % 31

    result = [str(num_full_words)]

    # Add full words (31 bytes each)
    for i in range(num_full_words):
        word_bytes = s_bytes[i*31:(i+1)*31]
        word_hex = '0x' + word_bytes.hex()
        result.append(word_hex)

    # Add pending word and length
    if pending_len > 0:
        pending_bytes = s_bytes[num_full_words*31:]
        pending_hex = '0x' + pending_bytes.hex()
        result.append(pending_hex)
        result.append(str(pending_len))
    else:
        result.append('0')
        result.append('0')

    return result


def build_constructor_calldata(config: DeploymentConfig) -> Tuple[int, List[str]]:
    """
    Build constructor calldata with proper ByteArray serialization.

    Args:
        config: Deployment configuration

    Returns:
        Tuple of (calldata_length, calldata_list)
    """
    calldata = []

    # Serialize ByteArray parameters
    name_encoded = encode_bytearray(config.name)
    symbol_encoded = encode_bytearray(config.symbol)
    base_uri_encoded = encode_bytearray(config.base_uri)

    # Build calldata
    calldata.extend(name_encoded)
    calldata.extend(symbol_encoded)
    calldata.extend(base_uri_encoded)
    calldata.append(config.royalty_receiver)
    calldata.append(str(config.royalty_fraction))

    # game_registry_address: Option<ContractAddress>
    if config.game_registry_address:
        calldata.append('0')  # Option::Some variant
        calldata.append(config.game_registry_address)
    else:
        calldata.append('1')  # Option::None variant

    # event_relayer_address: Option<ContractAddress>
    if config.event_relayer_address:
        calldata.append('0')  # Option::Some variant
        calldata.append(config.event_relayer_address)
    else:
        calldata.append('1')  # Option::None variant

    return len(calldata), calldata


def deploy_via_udc(config: DeploymentConfig) -> Tuple[bool, str, str]:
    """
    Deploy contract via Universal Deployer Contract using sncast.

    Args:
        config: Deployment configuration

    Returns:
        Tuple of (success, transaction_hash, error_message)
    """
    # Build constructor calldata
    calldata_len, constructor_calldata = build_constructor_calldata(config)

    # Build UDC deployContract calldata
    # deployContract(classHash, salt, unique, calldata_len, ...calldata)
    udc_calldata = [
        config.class_hash,
        str(config.salt),
        '1' if config.unique else '0',
        str(calldata_len),
    ]
    udc_calldata.extend(constructor_calldata)

    # Build sncast command
    cmd = [
        'sncast',
        '--profile', config.profile,
        'invoke',
        '--contract-address', config.udc_address,
        '--function', 'deployContract',
        '--calldata',
    ]
    cmd.extend(udc_calldata)

    print(f"Deploying contract...")
    print(f"  Class Hash: {config.class_hash}")
    print(f"  Constructor Args: {calldata_len} parameters")
    print(f"  UDC Address: {config.udc_address}")
    print(f"  Salt: {config.salt}")
    print(f"  Unique: {config.unique}")
    print()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd='/workspace/game-components/packages/token'
        )

        # Parse output to extract transaction hash
        output = result.stdout
        print(output)

        # Extract transaction hash from output
        for line in output.split('\n'):
            if 'Transaction Hash:' in line:
                tx_hash = line.split('Transaction Hash:')[1].strip()
                return True, tx_hash, ""

        # If transaction hash is not found, print full output for debugging
        print(f"\n--- Full sncast stdout ---")
        print(output)
        print(f"--- End sncast stdout ---")
        print(f"\n--- Full sncast stderr ---")
        print(result.stderr)
        print(f"--- End sncast stderr ---")

        return False, "", "Could not find transaction hash in output"

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        return False, "", error_msg


def get_contract_address_from_tx(tx_hash: str, profile: str) -> Optional[str]:
    """
    Extract deployed contract address from transaction receipt.

    The UDC emits a ContractDeployed event with the contract address as the first data field.

    Args:
        tx_hash: Transaction hash
        profile: sncast profile name

    Returns:
        Contract address or None if not found
    """
    print(f"\nFetching transaction receipt...")

    # Try starkli first (with full path)
    starkli_paths = [
        '/home/ubuntu/.starkli/bin/starkli',
        'starkli'
    ]

    for starkli_path in starkli_paths:
        cmd = [
            starkli_path,
            'transaction-receipt',
            tx_hash
        ]

        try:
            import os
            env = os.environ.copy()
            env['STARKNET_RPC'] = 'https://api.cartridge.gg/x/provable-dw/katana'

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env=env
            )

            receipt = json.loads(result.stdout)

            # Find ContractDeployed event from UDC
            if 'events' in receipt and len(receipt['events']) > 0:
                # The first event should be from the UDC
                udc_event = receipt['events'][0]
                if 'data' in udc_event and len(udc_event['data']) > 0:
                    # First data field is the deployed contract address
                    contract_address = udc_event['data'][0]
                    return contract_address

            return None

        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
            # Try next starkli path
            continue

    # If starkli doesn't work, provide manual instructions
    print(f"⚠️  Could not automatically extract contract address")
    print(f"\nTo get the contract address, run:")
    print(f"  export STARKNET_RPC=https://api.cartridge.gg/x/provable-dw/katana")
    print(f"  starkli transaction-receipt {tx_hash}")
    print(f"\nThe contract address is in events[0].data[0]")

    return None


def verify_deployment(contract_address: str, profile: str, expected_name: str) -> bool:
    """
    Verify contract deployment by calling the name() function.

    Args:
        contract_address: Deployed contract address
        profile: sncast profile name
        expected_name: Expected token name

    Returns:
        True if verification successful
    """
    print(f"\nVerifying deployment...")
    print(f"  Contract Address: {contract_address}")
    print(f"  Expected Name: {expected_name}")

    cmd = [
        'sncast',
        '--profile', profile,
        'call',
        '--contract-address', contract_address,
        '--function', 'name'
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd='/workspace/game-components/packages/token'
        )

        output = result.stdout
        print(output)

        # Check if expected name is in output
        if expected_name in output:
            print(f"✅ Verification successful!")
            return True
        else:
            print(f"⚠️  Warning: Name mismatch in verification")
            return False

    except subprocess.CalledProcessError as e:
        print(f"⚠️  Verification failed: {e.stderr}")
        return False


def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(
        description='Deploy FullTokenContract to Starknet/Katana'
    )
    parser.add_argument('--name', default='ProvableGameToken',
                        help='Token name (default: ProvableGameToken)')
    parser.add_argument('--symbol', default='PGT',
                        help='Token symbol (default: PGT)')
    parser.add_argument('--base-uri', default='https://api.provable.games/token/',
                        help='Base URI for token metadata')
    parser.add_argument('--royalty-receiver',
                        default='0x127fd5f1fe78a71f8bcd1fec63e3fe2f0486b6ecd5c86a0466c3a21fa5cfcec',
                        help='Royalty receiver address')
    parser.add_argument('--royalty-fraction', type=int, default=500,
                        help='Royalty fraction (default: 500 = 5%%)')
    parser.add_argument('--game-registry',
                        default='0x00348dafbd271cc82bfc57e3edd3a7b3163008f53c586e31d822862b72e1a663',
                        help='Game registry address (optional)')
    parser.add_argument('--event-relayer', default=None,
                        help='Event relayer address (optional)')
    parser.add_argument('--class-hash',
                        default='0x075137b5c45312610d7cb6d43982e5fd5bd0df6c0b1e51518ced64a91f125e85',
                        help='Contract class hash')
    parser.add_argument('--udc-address',
                        default='0x041a78e741e5af2fec34b695679bc6891742439f7afb8484ecd7766661ad02bf',
                        help='UDC contract address')
    parser.add_argument('--profile', default='default',
                        help='sncast profile name (default: default)')
    parser.add_argument('--salt', type=int, default=0,
                        help='Salt for deployment (default: 0)')
    parser.add_argument('--no-unique', action='store_true',
                        help='Do not make deployment unique to deployer')
    parser.add_argument('--no-verify', action='store_true',
                        help='Skip deployment verification')

    args = parser.parse_args()

    # Create deployment configuration
    config = DeploymentConfig(
        name=args.name,
        symbol=args.symbol,
        base_uri=args.base_uri,
        royalty_receiver=args.royalty_receiver,
        royalty_fraction=args.royalty_fraction,
        game_registry_address=args.game_registry if args.game_registry else None,
        event_relayer_address=args.event_relayer,
        class_hash=args.class_hash,
        udc_address=args.udc_address,
        profile=args.profile,
        salt=args.salt,
        unique=not args.no_unique
    )

    print("=" * 80)
    print("FullTokenContract Deployment Script")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Name: {config.name}")
    print(f"  Symbol: {config.symbol}")
    print(f"  Base URI: {config.base_uri}")
    print(f"  Royalty Receiver: {config.royalty_receiver}")
    print(f"  Royalty Fraction: {config.royalty_fraction} ({config.royalty_fraction/100}%)")
    print(f"  Game Registry: {config.game_registry_address or 'None'}")
    print(f"  Event Relayer: {config.event_relayer_address or 'None'}")
    print()

    # Deploy contract
    success, tx_hash, error = deploy_via_udc(config)

    if not success:
        print(f"\n❌ Deployment failed: {error}")
        sys.exit(1)

    print(f"\n✅ Deployment transaction submitted!")
    print(f"   Transaction Hash: {tx_hash}")

    # Get contract address from transaction
    contract_address = get_contract_address_from_tx(tx_hash, config.profile)

    if contract_address:
        print(f"\n🎉 Contract deployed successfully!")
        print(f"   Contract Address: {contract_address}")

        # Verify deployment
        if not args.no_verify:
            verify_deployment(contract_address, config.profile, config.name)

        # Write address to file for easy access
        with open('/workspace/game-components/LATEST_DEPLOYMENT.txt', 'w') as f:
            f.write(f"Contract Address: {contract_address}\n")
            f.write(f"Transaction Hash: {tx_hash}\n")
            f.write(f"Class Hash: {config.class_hash}\n")
            f.write(f"Name: {config.name}\n")
            f.write(f"Symbol: {config.symbol}\n")

        print(f"\n📝 Deployment details saved to: LATEST_DEPLOYMENT.txt")

    else:
        print(f"\n⚠️  Could not automatically extract contract address")
        print(f"   Query transaction manually: starkli transaction-receipt {tx_hash}")

    print("\n" + "=" * 80)
    print("Deployment Complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
