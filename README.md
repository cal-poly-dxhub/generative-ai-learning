# Generative AI Introduction

Thanks for your interest in this material. Here are a few notebooks used to teach business students the basic fundamentals of Generative AI.  If you have any comments or questions or would like to collaborate please send me an email.

- Darren Kraker - dkraker@calpoly.edu

**This document:**

# Disclaimers

**Customers are responsible for making their own independent assessment of the information in this document.**

**This document:**


Customers are responsible for making their own independent assessment of the information in this document. 

This document: 

(a) is for informational purposes only, 

(b) references AWS product offerings and practices, which are subject to change without notice, 

(c) does not create any commitments or assurances from AWS and its affiliates, suppliers or licensors. AWS products or services are provided “as is” without warranties, representations, or conditions of any kind, whether express or implied. The responsibilities and liabilities of AWS to its customers are controlled by AWS agreements, and this document is not part of, nor does it modify, any agreement between AWS and its customers, and 

(d) is not to be considered a recommendation or viewpoint of AWS. 

Additionally, you are solely responsible for testing, security and optimizing all code and assets on GitHub repo, and all such code and assets should be considered: 

(a) as-is and without warranties or representations of any kind, 

(b) not suitable for production environments, or on production or other critical data, and 

(c) to include shortcuts in order to support rapid prototyping such as, but not limited to, relaxed authentication and authorization and a lack of strict adherence to security best practices. 

All work produced is open source. More information can be found in the GitHub repo. 


## Table of Contents

- [Collaboration](#collaboration)
- [Disclaimers](#disclaimers)
- [Authors](#authors)
- [Overview](#overview)
- [Environment Step](environment-step)
- [Set Required AWS Permissions](set-required-aws-permissions)
- [Make sure you have access to Bedrock Models](make-sure-you-havea-ccess-to-bedrock-models)


## Overview

- This course was developed to teach Masters Students in the College of Business some techniques that are useful in building Generative AI Applications.  The course was conducted using an AWS account and primary relied on SageMaker AI Studio for students to access.  These notebooks should work in an standard ML Notebook Instance.  If you're interested in automation scripts to build out an SageMaker Studio environment please reach out and I'd be happy to share that code as well.

### Environment Step

- Deploy a SageMaker Instance Notebook
- git clone https://github.com/cal-poly-dxhub/generative-ai-learning.git
- Setup Aurora PostgreSQL qith PgVector

###  Set Required AWS Permissions
Ensure the Sagemaker Policy has access to:
- AmazonBedrockFullAccess
- AmazonS3FullAccess

### Make sure you have access to Bedrock Models
- Titan Text Embeddings V2 
- Cohere Embed English (cohere.embed-english-v3)
- Claude Sonnet 3 (anthropic.claude-3-sonnet-20240229-v1:0_

For any queries or issues, please contact:

- Darren Kraker - dkraker@calpoly.edu
- Nick Osterbur - nosterbu@calpoly.edu

