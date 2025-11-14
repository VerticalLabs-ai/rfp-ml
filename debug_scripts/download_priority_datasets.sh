#!/bin/bash
# Priority dataset download script
# Generated automatically from dataset catalog analysis

mkdir -p /app/government_rfp_bid_1927/data/raw
cd /app/government_rfp_bid_1927/data/raw

echo 'Downloading immediate priority files...'
wget -O 'ContractOpportunitiesFullCSV.csv' 'https://storage.googleapis.com/dataset_rfp/sam_gov/ContractOpportunitiesFullCSV.csv' || curl -o 'ContractOpportunitiesFullCSV.csv' 'https://storage.googleapis.com/dataset_rfp/sam_gov/ContractOpportunitiesFullCSV.csv'
wget -O 'Contract_Opportunities_Data_Extract_Documentation.pdf' 'https://storage.googleapis.com/dataset_rfp/sam_gov/Contract Opportunities Data Extract Documentation.pdf' || curl -o 'Contract_Opportunities_Data_Extract_Documentation.pdf' 'https://storage.googleapis.com/dataset_rfp/sam_gov/Contract Opportunities Data Extract Documentation.pdf'

echo 'Downloading high priority files...'
wget -O 'FY2025_archived_opportunities.csv' 'https://storage.googleapis.com/dataset_rfp/sam_gov/FY2025_archived_opportunities.csv' || curl -o 'FY2025_archived_opportunities.csv' 'https://storage.googleapis.com/dataset_rfp/sam_gov/FY2025_archived_opportunities.csv'
wget -O 'FY2024_archived_opportunities.csv' 'https://storage.googleapis.com/dataset_rfp/sam_gov/FY2024_archived_opportunities.csv' || curl -o 'FY2024_archived_opportunities.csv' 'https://storage.googleapis.com/dataset_rfp/sam_gov/FY2024_archived_opportunities.csv'
wget -O 'FY2023_archived_opportunities.csv' 'https://storage.googleapis.com/dataset_rfp/sam_gov/FY2023_archived_opportunities.csv' || curl -o 'FY2023_archived_opportunities.csv' 'https://storage.googleapis.com/dataset_rfp/sam_gov/FY2023_archived_opportunities.csv'

echo 'Download complete!'
ls -lah
