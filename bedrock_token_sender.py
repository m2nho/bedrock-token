import boto3
import json
import time
from botocore.exceptions import ClientError

class BedrockTokenSender:
    def __init__(self, access_key, secret_key, region):
        self.region = region
        self.bedrock = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        self.bedrock_client = boto3.client(
            'bedrock',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        self.sts_client = boto3.client(
            'sts',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        self.s3_bucket = None
    
    def setup_s3_bucket(self):
        """계정 ID 기반으로 S3 버킷을 생성합니다."""
        try:
            account_id = self.sts_client.get_caller_identity()['Account']
            bucket_name = f"bedrock-output-{account_id}-{self.region}"
            
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                print(f"S3 버킷 사용: {bucket_name}")
            except ClientError:
                create_config = {}
                if self.region != 'us-east-1':
                    create_config['CreateBucketConfiguration'] = {'LocationConstraint': self.region}
                
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    **create_config
                )
                print(f"S3 버킷 생성: {bucket_name}")
            
            self.s3_bucket = bucket_name
            return bucket_name
        except ClientError as e:
            print(f"S3 버킷 설정 실패: {e}")
            return None
    
    def get_available_models(self):
        """실제 호출 가능한 Bedrock 모델 ID를 가져옵니다."""
        try:
            response = self.bedrock_client.list_foundation_models()
            
            available_models = []
            for model in response['modelSummaries']:
                model_id = model['modelId']
                
                # 호출 불가능한 모델 제외
                skip_patterns = [
                    ':mm',  # 멀티모달 버전
                    ':512', # 토큰 제한 버전
                    'titan-image-generator-v1:0',  # 버전 표기 문제
                    'titan-embed-image-v1:0',      # 버전 표기 문제
                    'stable-diffusion-xl-v1:0'     # 버전 표기 문제
                ]
                
                if model_id.endswith('k') or any(pattern in model_id for pattern in skip_patterns):
                    continue
                    
                available_models.append(model_id)
                
            return available_models
        except ClientError as e:
            print(f"모델 목록 가져오기 실패: {e}")
            return []
    
    def send_token_to_model(self, model_id):
        """특정 모델에 토큰을 보냅니다."""
        try:
            # 리전에 따른 cross-region inference profile 매핑
            if self.region == 'ap-northeast-2':
                cross_region_mapping = {
                    'amazon.nova-pro-v1:0': 'apac.amazon.nova-pro-v1:0',
                    'amazon.nova-lite-v1:0': 'apac.amazon.nova-lite-v1:0',
                    'amazon.nova-micro-v1:0': 'apac.amazon.nova-micro-v1:0',
                    'anthropic.claude-3-sonnet-20240229-v1:0': 'apac.anthropic.claude-3-sonnet-20240229-v1:0',
                    'anthropic.claude-3-5-sonnet-20241022-v2:0': 'apac.anthropic.claude-3-5-sonnet-20241022-v2:0',
                    'anthropic.claude-3-7-sonnet-20250219-v1:0': 'apac.anthropic.claude-3-7-sonnet-20250219-v1:0',
                    'anthropic.claude-sonnet-4-20250514-v1:0': 'apac.anthropic.claude-sonnet-4-20250514-v1:0',
                    'meta.llama3-1-8b-instruct-v1:0': 'apac.meta.llama3-1-8b-instruct-v1:0',
                    'meta.llama3-1-70b-instruct-v1:0': 'apac.meta.llama3-1-70b-instruct-v1:0',
                    'meta.llama3-2-11b-instruct-v1:0': 'apac.meta.llama3-2-11b-instruct-v1:0',
                    'meta.llama3-2-90b-instruct-v1:0': 'apac.meta.llama3-2-90b-instruct-v1:0',
                    'meta.llama3-2-1b-instruct-v1:0': 'apac.meta.llama3-2-1b-instruct-v1:0',
                    'meta.llama3-2-3b-instruct-v1:0': 'apac.meta.llama3-2-3b-instruct-v1:0',
                    'meta.llama3-3-70b-instruct-v1:0': 'apac.meta.llama3-3-70b-instruct-v1:0',
                    'meta.llama4-scout-17b-instruct-v1:0': 'apac.meta.llama4-scout-17b-instruct-v1:0',
                    'meta.llama4-maverick-17b-instruct-v1:0': 'apac.meta.llama4-maverick-17b-instruct-v1:0',
                    'deepseek.r1-v1:0': 'apac.deepseek.r1-v1:0',
                    'amazon.nova-premier-v1:0': 'apac.amazon.nova-premier-v1:0',
                    'amazon.titan-image-generator-v1:0': 'apac.amazon.titan-image-generator-v1:0',
                    'amazon.titan-embed-image-v1:0': 'apac.amazon.titan-embed-image-v1:0',
                    'stability.stable-diffusion-xl-v1:0': 'apac.stability.stable-diffusion-xl-v1:0',
                    'mistral.pixtral-large-2502-v1:0': 'apac.mistral.pixtral-large-2502-v1:0',
                    'cohere.embed-english-v3:0:512': 'apac.cohere.embed-english-v3:0:512',
                    'cohere.embed-multilingual-v3:0:512': 'apac.cohere.embed-multilingual-v3:0:512',
                    'amazon.nova-canvas-v1:0': 'apac.amazon.nova-canvas-v1:0',
                    'amazon.nova-reel-v1:0': 'apac.amazon.nova-reel-v1:0',
                    'amazon.nova-reel-v1:1': 'apac.amazon.nova-reel-v1:1',
                    'amazon.nova-sonic-v1:0': 'apac.amazon.nova-sonic-v1:0',
                    'anthropic.claude-3-opus-20240229-v1:0': 'apac.anthropic.claude-3-opus-20240229-v1:0',
                    'anthropic.claude-opus-4-20250514-v1:0': 'apac.anthropic.claude-opus-4-20250514-v1:0'
                }
            elif self.region == 'us-east-1':
                cross_region_mapping = {
                    'amazon.nova-pro-v1:0': 'us.amazon.nova-pro-v1:0',
                    'amazon.nova-lite-v1:0': 'us.amazon.nova-lite-v1:0',
                    'amazon.nova-micro-v1:0': 'us.amazon.nova-micro-v1:0',
                    'anthropic.claude-3-sonnet-20240229-v1:0': 'us.anthropic.claude-3-sonnet-20240229-v1:0',
                    'anthropic.claude-3-5-sonnet-20241022-v2:0': 'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
                    'anthropic.claude-3-7-sonnet-20250219-v1:0': 'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
                    'anthropic.claude-sonnet-4-20250514-v1:0': 'us.anthropic.claude-sonnet-4-20250514-v1:0',
                    'anthropic.claude-3-5-haiku-20241022-v1:0': 'us.anthropic.claude-3-5-haiku-20241022-v1:0',
                    'meta.llama3-1-8b-instruct-v1:0': 'us.meta.llama3-1-8b-instruct-v1:0',
                    'meta.llama3-1-70b-instruct-v1:0': 'us.meta.llama3-1-70b-instruct-v1:0',
                    'meta.llama3-2-11b-instruct-v1:0': 'us.meta.llama3-2-11b-instruct-v1:0',
                    'meta.llama3-2-90b-instruct-v1:0': 'us.meta.llama3-2-90b-instruct-v1:0',
                    'meta.llama3-2-1b-instruct-v1:0': 'us.meta.llama3-2-1b-instruct-v1:0',
                    'meta.llama3-2-3b-instruct-v1:0': 'us.meta.llama3-2-3b-instruct-v1:0',
                    'meta.llama3-3-70b-instruct-v1:0': 'us.meta.llama3-3-70b-instruct-v1:0',
                    'meta.llama4-scout-17b-instruct-v1:0': 'us.meta.llama4-scout-17b-instruct-v1:0',
                    'meta.llama4-maverick-17b-instruct-v1:0': 'us.meta.llama4-maverick-17b-instruct-v1:0',
                    'deepseek.r1-v1:0': 'us.deepseek.r1-v1:0',
                    'amazon.nova-premier-v1:0': 'us.amazon.nova-premier-v1:0',
                    'amazon.titan-image-generator-v1:0': 'us.amazon.titan-image-generator-v1:0',
                    'amazon.titan-embed-image-v1:0': 'us.amazon.titan-embed-image-v1:0',
                    'stability.stable-diffusion-xl-v1:0': 'us.stability.stable-diffusion-xl-v1:0',
                    'mistral.pixtral-large-2502-v1:0': 'us.mistral.pixtral-large-2502-v1:0',
                    'cohere.embed-english-v3:0:512': 'us.cohere.embed-english-v3:0:512',
                    'cohere.embed-multilingual-v3:0:512': 'us.cohere.embed-multilingual-v3:0:512',
                    'amazon.nova-canvas-v1:0': 'us.amazon.nova-canvas-v1:0',
                    'amazon.nova-reel-v1:0': 'us.amazon.nova-reel-v1:0',
                    'amazon.nova-reel-v1:1': 'us.amazon.nova-reel-v1:1',
                    'amazon.nova-sonic-v1:0': 'us.amazon.nova-sonic-v1:0',
                    'anthropic.claude-3-opus-20240229-v1:0': 'us.anthropic.claude-3-opus-20240229-v1:0',
                    'anthropic.claude-opus-4-20250514-v1:0': 'us.anthropic.claude-opus-4-20250514-v1:0'
                }
            else:
                # 다른 리전에서는 cross-region 사용 안함
                cross_region_mapping = {}
            
            # Cross-region 모델은 inference profile ID 사용
            actual_model_id = cross_region_mapping.get(model_id, model_id)
            
            if 'claude' in model_id.lower():
                body = json.dumps({
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10,
                    "anthropic_version": "bedrock-2023-05-31"
                })
            elif 'nova' in model_id.lower():
                if 'canvas' in model_id.lower():
                    body = json.dumps({
                        "taskType": "TEXT_IMAGE",
                        "textToImageParams": {
                            "text": "Hello world"
                        },
                        "imageGenerationConfig": {
                            "numberOfImages": 1,
                            "height": 512,
                            "width": 512
                        }
                    })
                elif 'reel' in model_id.lower():
                    # Nova Reel은 비동기 호출 사용
                    return self.send_nova_reel_async(model_id)
                elif 'sonic' in model_id.lower():
                    # Nova Sonic은 스트리밍 API 필요
                    print(f"- {model_id}: 스트리밍 API 필요 (스킵)")
                    return False
                else:
                    body = json.dumps({
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"text": "Hello"}
                                ]
                            }
                        ],
                        "inferenceConfig": {
                            "max_new_tokens": 10
                        }
                    })
            elif 'titan-embed' in model_id.lower():
                body = json.dumps({
                    "inputText": "Hello world"
                })
            elif 'marengo-embed' in model_id.lower():
                # TwelveLabs 모델은 비동기 호출 사용
                return self.send_async_token(model_id)
            elif 'titan' in model_id.lower():
                if 'image-generator' in model_id.lower():
                    body = json.dumps({
                        "taskType": "TEXT_IMAGE",
                        "textToImageParams": {
                            "text": "Hello world"
                        },
                        "imageGenerationConfig": {
                            "numberOfImages": 1,
                            "height": 512,
                            "width": 512
                        }
                    })
                else:
                    body = json.dumps({
                        "inputText": "Hello",
                        "textGenerationConfig": {"maxTokenCount": 10}
                    })
            elif 'llama' in model_id.lower():
                body = json.dumps({
                    "prompt": "Hello",
                    "max_gen_len": 10,
                    "temperature": 0.1
                })
            elif 'jamba' in model_id.lower():
                body = json.dumps({
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10
                })
            elif 'cohere' in model_id.lower():
                if 'embed' in model_id.lower():
                    body = json.dumps({
                        "texts": ["Hello world"],
                        "input_type": "search_document"
                    })
                elif 'command-r' in model_id.lower():
                    body = json.dumps({
                        "message": "Hello",
                        "max_tokens": 10
                    })
                else:
                    body = json.dumps({
                        "prompt": "Hello",
                        "max_tokens": 10
                    })
            elif 'stable-diffusion' in model_id.lower():
                body = json.dumps({
                    "text_prompts": [{"text": "Hello world"}],
                    "cfg_scale": 10,
                    "seed": 0,
                    "steps": 50
                })
            elif 'deepseek' in model_id.lower():
                body = json.dumps({
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10,
                    "temperature": 0.1
                })
            elif 'pixtral' in model_id.lower():
                body = json.dumps({
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10
                })
            else:
                body = json.dumps({
                    "prompt": "Hello",
                    "max_tokens": 10
                })
            
            self.bedrock.invoke_model(
                modelId=actual_model_id,
                body=body,
                contentType='application/json'
            )
            
            if actual_model_id != model_id:
                print(f"✓ {model_id}: 성공 (cross-region: {actual_model_id})")
            else:
                print(f"✓ {model_id}: 성공")
            return True
            
        except ClientError as e:
            # 모델별 대체 형식 시도
            alternative_formats = []
            
            if 'nova' in model_id.lower():
                if 'canvas' in model_id.lower():
                    alternative_formats = [
                        {
                            "taskType": "TEXT_IMAGE",
                            "textToImageParams": {"text": "Hello world"},
                            "imageGenerationConfig": {"numberOfImages": 1, "height": 512, "width": 512}
                        }
                    ]
                elif 'reel' in model_id.lower():
                    alternative_formats = [
                        {
                            "taskType": "TEXT_VIDEO",
                            "textToVideoParams": {"text": "Hello world"},
                            "videoGenerationConfig": {"durationSeconds": 6, "fps": 24, "dimension": "1280x720"}
                        }
                    ]
                elif 'sonic' in model_id.lower():
                    alternative_formats = [
                        {
                            "text": "Hello world",
                            "voice": "Matthew",
                            "outputFormat": "mp3"
                        }
                    ]
                else:
                    alternative_formats = [
                        {
                            "messages": [{"role": "user", "content": [{"text": "Hello"}]}],
                            "inferenceConfig": {"max_new_tokens": 10}
                        },
                        {
                            "messages": [{"role": "user", "content": "Hello"}],
                            "max_tokens": 10
                        }
                    ]
                alternative_formats = [
                    {
                        "messages": [{"role": "user", "content": [{"text": "Hello"}]}],
                        "inferenceConfig": {"max_new_tokens": 10}
                    },
                    {
                        "messages": [{"role": "user", "content": "Hello"}],
                        "max_tokens": 10
                    }
                ]
            elif 'llama' in model_id.lower():
                if 'llama3-1' in model_id.lower() or 'llama3-2' in model_id.lower() or 'llama3-3' in model_id.lower() or 'llama4' in model_id.lower():
                    alternative_formats = [
                        {
                            "messages": [{"role": "user", "content": "Hello"}],
                            "max_tokens": 10,
                            "temperature": 0.1
                        },
                        {
                            "prompt": "<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\nHello<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
                            "max_gen_len": 10
                        }
                    ]
                else:
                    alternative_formats = [
                        {
                            "prompt": "<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\nHello<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
                            "max_gen_len": 10
                        },
                        {
                            "messages": [{"role": "user", "content": "Hello"}],
                            "max_tokens": 10
                        }
                    ]
            elif 'jamba' in model_id.lower():
                alternative_formats = [
                    {
                        "prompt": "Hello",
                        "max_tokens": 10
                    }
                ]
            elif 'deepseek' in model_id.lower():
                alternative_formats = [
                    {
                        "prompt": "Hello",
                        "max_tokens": 10,
                        "temperature": 0.1
                    }
                ]
            elif 'cohere' in model_id.lower() and 'embed' in model_id.lower():
                alternative_formats = [
                    {
                        "texts": ["Hello world"],
                        "input_type": "classification"
                    },
                    {
                        "texts": ["Hello world"]
                    }
                ]
            elif 'command-r' in model_id.lower():
                alternative_formats = [
                    {
                        "prompt": "Hello",
                        "max_tokens": 10
                    }
                ]
            
            for alt_body in alternative_formats:
                try:
                    self.bedrock.invoke_model(
                        modelId=actual_model_id,
                        body=json.dumps(alt_body),
                        contentType='application/json'
                    )
                    if actual_model_id != model_id:
                        print(f"✓ {model_id}: 성공 (cross-region: {actual_model_id})")
                    else:
                        print(f"✓ {model_id}: 성공")
                    return True
                except ClientError:
                    continue
            

            
            # 실제 접근 불가능한 모델만 스킵
            if 'premier:mm' in model_id.lower():
                print(f"- {model_id}: 접근 권한 없음 (스킵)")
                return False
            
            print(f"✗ {model_id}: 실패 - {e.response['Error']['Code']}")
            return False
    
    def send_async_token(self, model_id):
        """비동기 모델 호출 (TwelveLabs)"""
        if not self.s3_bucket:
            print(f"✗ {model_id}: S3 버킷 설정 필요")
            return False
        
        try:
            model_input = {
                "inputType": "text",
                "inputText": "Hello world"
            }
            
            response = self.bedrock.start_async_invoke(
                modelId=model_id,
                modelInput=model_input,
                outputDataConfig={
                    "s3OutputDataConfig": {
                        "s3Uri": f"s3://{self.s3_bucket}/bedrock-output/"
                    }
                }
            )
            
            invocation_arn = response['invocationArn']
            
            # 상태 확인 (최대 60초 대기)
            for _ in range(20):
                status_response = self.bedrock.get_async_invoke(
                    invocationArn=invocation_arn
                )
                status = status_response['status']
                
                if status == 'Completed':
                    print(f"✓ {model_id}: 성공 (비동기)")
                    return True
                elif status == 'Failed':
                    print(f"✗ {model_id}: 실패 (비동기)")
                    return False
                
                time.sleep(3)
            
            print(f"- {model_id}: 비동기 작업 진행중 (스킵)")
            return False
            
        except ClientError as e:
            print(f"✗ {model_id}: 비동기 호출 실패 - {e.response['Error']['Code']}")
            return False
    
    def send_nova_reel_async(self, model_id):
        """비동기 Nova Reel 모델 호출"""
        if not self.s3_bucket:
            print(f"✗ {model_id}: S3 버킷 설정 필요")
            return False
        
        try:
            model_input = {
                "taskType": "TEXT_VIDEO",
                "textToVideoParams": {
                    "text": "Hello world"
                },
                "videoGenerationConfig": {
                    "durationSeconds": 6,
                    "fps": 24,
                    "dimension": "1280x720"
                }
            }
            
            response = self.bedrock.start_async_invoke(
                modelId=model_id,
                modelInput=model_input,
                outputDataConfig={
                    "s3OutputDataConfig": {
                        "s3Uri": f"s3://{self.s3_bucket}/bedrock-output/"
                    }
                }
            )
            
            invocation_arn = response['invocationArn']
            
            # 상태 확인 (최대 60초 대기)
            for _ in range(20):
                status_response = self.bedrock.get_async_invoke(
                    invocationArn=invocation_arn
                )
                status = status_response['status']
                
                if status == 'Completed':
                    print(f"✓ {model_id}: 성공 (비동기)")
                    return True
                elif status == 'Failed':
                    print(f"✗ {model_id}: 실패 (비동기)")
                    return False
                
                time.sleep(3)
            
            print(f"- {model_id}: 비동기 작업 진행중 (스킵)")
            return False
            
        except ClientError as e:
            print(f"✗ {model_id}: 비동기 호출 실패 - {e.response['Error']['Code']}")
            return False
    
    def send_tokens_to_all_models(self):
        """모든 모델에 토큰을 보냅니다."""
        # S3 버킷 설정
        self.setup_s3_bucket()
        
        models = self.get_available_models()
        if not models:
            print("사용 가능한 모델이 없습니다.")
            return
        
        print(f"\n호출 가능한 모델 목록 ({len(models)}개):")
        for i, model_id in enumerate(models, 1):
            print(f"{i}. {model_id}")
        
        print(f"\n토큰 전송 시작...\n")
        
        success_count = 0
        for model_id in models:
            if self.send_token_to_model(model_id):
                success_count += 1
        
        print(f"\n완료: {success_count}/{len(models)} 모델 성공")

def main():
    # 사용자 입력 받기
    access_key = input("AWS Access Key ID: ")
    secret_key = input("AWS Secret Access Key: ")
    region = input("AWS Region (예: us-east-1): ")
    
    # 토큰 전송 실행
    sender = BedrockTokenSender(access_key, secret_key, region)
    sender.send_tokens_to_all_models()

if __name__ == "__main__":
    main()