#!/bin/bash
# Simulate end_session.sh prompts without side effects

echo "Test: Update current goals in .clauderc? (y/N)"
read -r response
echo "Response: $response"

echo "Test: What did you accomplish this session? (or press Enter to skip)"
read -r response2
echo "Response2: '$response2'"

echo "All prompts answered."