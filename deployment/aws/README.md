# AWS Deployment Notes

This project is ready to package as a containerized API and Streamlit service.

Recommended path:

1. Build the Docker image from `deployment/docker/Dockerfile`.
2. Push the image to Amazon ECR.
3. Deploy the API container to ECS Fargate or Elastic Beanstalk.
4. Store environment-specific values in AWS Systems Manager Parameter Store or Secrets Manager.
5. Mount or bake model artifacts from `models/` after a training run.

For a lightweight demo, deploy only the FastAPI service and expose `/health`, `/predict`, `/batch_predict`, `/recommend`, and `/similar_properties`.

