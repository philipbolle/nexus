#!/bin/bash
# Simple test prompt script

echo "Test prompt: Update something? (y/N)"
read -r response
echo "You responded: $response"

echo "Another test: press Enter to skip"
read -r response2
echo "You responded: '$response2'"

echo "Test complete."