import boto3
import csv
import json
import logging
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class StorageGatewayManager:
    def __init__(self, region_name='us-east-1'):
        self.client = boto3.client('storagegateway', region_name=region_name)
        self.region = region_name

    def list_all_gateways(self):
        """Retrieves all gateway ARNs using a paginator."""
        try:
            gateways = []
            paginator = self.client.get_paginator('list_gateways')
            for page in paginator.paginate():
                gateways.extend(page.get('Gateways', []))
            return gateways
        except ClientError as e:
            logging.error(f"Failed to list gateways: {e}")
            return []

    def get_detailed_status(self):
        """Returns high-level metadata for all gateways in the account."""
        gateways = self.list_all_gateways()
        detailed_list = []
        for gw in gateways:
            try:
                info = self.client.describe_gateway_information(GatewayARN=gw['GatewayARN'])
                detailed_list.append({
                    'Name': info.get('GatewayName', 'N/A'),
                    'ID': info.get('GatewayId', 'N/A'),
                    'Status': info.get('GatewayState', 'UNKNOWN'),
                    'Type': info.get('GatewayType', 'N/A'),
                    'ARN': gw['GatewayARN']
                })
            except ClientError as e:
                logging.warning(f"Could not describe gateway {gw['GatewayARN']}: {e}")
        return detailed_list

    def _get_share_details(self, share_arns, share_type):
        """Batches and fetches deep details for specific shares (NFS or SMB)."""
        details = []
        # AWS limits describe calls to 10 ARNs at a time
        for i in range(0, len(share_arns), 10):
            batch = share_arns[i:i+10]
            try:
                if share_type == 'NFS':
                    response = self.client.describe_nfs_file_shares(FileShareARNList=batch)
                    details.extend(response.get('NFSFileShareInfoList', []))
                else:
                    response = self.client.describe_smb_file_shares(FileShareARNList=batch)
                    details.extend(response.get('SMBFileShareInfoList', []))
            except ClientError as e:
                logging.error(f"Failed to describe {share_type} shares: {e}")
        return details

    def export_shares_to_json(self, filename='gateway_shares.json'):
        """
        Creates a JSON map of gateways and their shares, including 
        IP allowed lists (NFS) and AD User/Group access (SMB).
        """
        gateways = self.get_detailed_status()
        share_report = {}

        for gw in gateways:
            if gw['Type'] in ['FILE_S3', 'FILE_FSX_SMB']:
                logging.info(f"Processing shares for {gw['Name']}...")
                try:
                    # 1. List basic share ARNs for this gateway
                    paginator = self.client.get_paginator('list_file_shares')
                    shares_info = []
                    for page in paginator.paginate(GatewayARN=gw['ARN']):
                        shares_info.extend(page.get('FileShareInfoList', []))
                    
                    # 2. Separate ARNs by type for batch describing
                    nfs_arns = [s['FileShareARN'] for s in shares_info if s['FileShareType'] == 'NFS']
                    smb_arns = [s['FileShareARN'] for s in shares_info if s['FileShareType'] == 'SMB']

                    # 3. Fetch deep details (Permissions/Access)
                    full_details = []
                    
                    for share in self._get_share_details(nfs_arns, 'NFS'):
                        full_details.append({
                            'ShareID': share.get('FileShareId'),
                            'Type': 'NFS',
                            'Path': share.get('Path'),
                            'Bucket': share.get('LocationARN'),
                            'AllowedClients': share.get('ClientList', []), # IP Ranges
                            'Status': share.get('FileShareStatus')
                        })

                    for share in self._get_share_details(smb_arns, 'SMB'):
                        full_details.append({
                            'ShareID': share.get('FileShareId'),
                            'Type': 'SMB',
                            'Path': share.get('Path'),
                            'Bucket': share.get('LocationARN'),
                            'AD_AllowedUsers': share.get('ValidUserList', []),
                            'AD_AllowedGroups': [u for u in share.get('ValidUserList', []) if u.startswith('@')],
                            'AD_AdminUsers': share.get('AdminUserList', []),
                            'Status': share.get('FileShareStatus'),
                            'SMB_ACL_Enabled': share.get('SMBACLEnabled', False)
                        })

                    share_report[gw['Name']] = {
                        'GatewayID': gw['ID'],
                        'Shares': full_details
                    }

                except ClientError as e:
                    logging.error(f"Error gathering share data for {gw['Name']}: {e}")

        with open(filename, 'w') as f:
            json.dump(share_report, f, indent=4)
        logging.info(f"Detailed share report saved to {filename}")

if __name__ == "__main__":
    sg_mgr = StorageGatewayManager(region_name='us-east-1')
    sg_mgr.export_shares_to_json('comprehensive_shares.json')
