import boto3
import csv
import logging
from botocore.exceptions import ClientError

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

############################################################################################
# Example Usage...
# from AWS_SG_MGR import StorageGatewayManager
#
# manager = StorageGatewayManager(region_name='us-east-1')
# gateways = manager.get_detailed_status()
# Process your gateways here...
############################################################################################

class StorageGatewayManager:
    def __init__(self, region_name='us-east-1'):
        """Initializes the boto3 client for Storage Gateway."""
        self.client = boto3.client('storagegateway', region_name=region_name)
        self.region = region_name

    def list_all_gateways(self):
        """Retrieves a list of all gateway ARNs in the region using a paginator."""
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
        """Returns a list of dictionaries containing detailed info for each gateway."""
        gateways = self.list_all_gateways()
        detailed_list = []

        for gw in gateways:
            try:
                info = self.client.describe_gateway_information(
                    GatewayARN=gw['GatewayARN']
                )
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

    def export_to_csv(self, filename='gateway_report.csv'):
        """Fetches detailed status and exports it to a CSV file."""
        data = self.get_detailed_status()
        if not data:
            logging.info("No data found to export.")
            return

        keys = data[0].keys()
        try:
            with open(filename, 'w', newline='') as output_file:
                dict_writer = csv.DictWriter(output_file, fieldnames=keys)
                dict_writer.writeheader()
                dict_writer.writerows(data)
            logging.info(f"Report successfully exported to {filename}")
        except IOError as e:
            logging.error(f"Error writing CSV file: {e}")

if __name__ == "__main__":
    sg_mgr = StorageGatewayManager(region_name='us-east-1')
    
    # Run the export
    sg_mgr.export_to_csv('my_gateways.csv')
