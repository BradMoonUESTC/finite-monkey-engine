import json
import os
import numpy as np
import requests
from utils.cache_manager import CacheManager

# Initialize cache manager
cache_manager = CacheManager()

def azure_openai(prompt):
    # Azure OpenAI配置
    api_key = os.environ.get('AZURE_API_KEY')
    api_base = os.environ.get('AZURE_API_BASE')
    api_version = os.environ.get('AZURE_API_VERSION')
    deployment_name = os.environ.get('AZURE_DEPLOYMENT_NAME')
    
    # Prepare request data
    request_data = {
        "messages": [
            {"role": "system", "content": "你是一个熟悉智能合约与区块链安全的安全专家。"},
            {"role": "user", "content": prompt}
        ]
    }
    
    # Check cache first
    cached_response = cache_manager.get_cached_response('azure', request_data)
    if cached_response:
        return cached_response

    # 构建URL
    url = f"{api_base}openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"
    # 设置请求头
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    try:
        # 发送POST请求
        response = requests.post(url, headers=headers, json=request_data)
        # 检查响应状态
        response.raise_for_status()
        # 解析JSON响应
        result = response.json()
        response_content = result['choices'][0]['message']['content']
        
        # Cache the response
        cache_manager.cache_response('azure', request_data, response_content)
        
        return response_content
    except requests.exceptions.RequestException as e:
        print("Azure OpenAI测试失败。错误:", str(e))
        return None
    

def azure_openai_json(prompt):
    # Azure OpenAI配置
    api_key = os.environ.get('AZURE_API_KEY')
    api_base = os.environ.get('AZURE_API_BASE')
    api_version = os.environ.get('AZURE_API_VERSION')
    deployment_name = os.environ.get('AZURE_DEPLOYMENT_NAME')
    
    # Prepare request data
    request_data = {
        "response_format": { "type": "json_object" },
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant designed to output JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    # Check cache first
    cached_response = cache_manager.get_cached_response('azure', request_data)
    if cached_response:
        return cached_response

    # 构建URL
    url = f"{api_base}openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"
    # 设置请求头
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    try:
        # 发送POST请求
        response = requests.post(url, headers=headers, json=request_data)
        # 检查响应状态
        response.raise_for_status()
        # 解析JSON响应
        result = response.json()
        response_content = result['choices'][0]['message']['content']
        
        # Cache the response
        cache_manager.cache_response('azure', request_data, response_content)
        
        return response_content
    except requests.exceptions.RequestException as e:
        print("Azure OpenAI测试失败。错误:", str(e))
        return None

    
def ask_openai_common(prompt):
    api_base = os.environ.get('OPENAI_API_BASE', 'api.openai.com')
    api_key = os.environ.get('OPENAI_API_KEY')
    
    # Prepare request data
    request_data = {
        "model": os.environ.get('VUL_MODEL_ID'),
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    # Check cache first
    cached_response = cache_manager.get_cached_response('openai', request_data)
    if cached_response:
        return cached_response
        
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    response = requests.post(f'https://{api_base}/v1/chat/completions', headers=headers, json=request_data)
    try:
        response_json = response.json()
        response_content = response_json['choices'][0]['message']['content']
        
        # Cache the response
        cache_manager.cache_response('openai', request_data, response_content)
        
        return response_content
    except Exception as e:
        print(f"Error in ask_openai_common: {str(e)}")
        return None
        
def ask_deepseek_common(prompt):
    api_base = os.environ.get('OPENAI_API_BASE', 'api.openai.com')
    api_key = os.environ.get('OPENAI_API_KEY')
    
    # Prepare request data
    request_data = {
        "model": os.environ.get('VUL_MODEL_ID'),
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "temperature":0,
    }
    
    # Check cache first
    cached_response = cache_manager.get_cached_response('deepseek', request_data)
    if cached_response:
        return cached_response
        
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    response = requests.post(f'https://{api_base}/v1/chat/completions', headers=headers, json=request_data)
    try:
        response_json = response.json()
        response_content = response_json['choices'][0]['message']['content']
        
        # Cache the response
        cache_manager.cache_response('deepseek', request_data, response_content)
        
        return response_content
    except Exception as e:
        print(f"Error in ask_deepseek_common: {str(e)}")
        return None

def ask_openai_for_json(prompt):
    api_base = os.environ.get('OPENAI_API_BASE', 'api.openai.com')
    api_key = os.environ.get('OPENAI_API_KEY')
    
    # Prepare request data
    request_data = {
        "model": os.environ.get('VUL_MODEL_ID'),
        "response_format": { "type": "json_object" },
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant designed to output JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    # Check cache first
    cached_response = cache_manager.get_cached_response('openai', request_data)
    if cached_response:
        return cached_response
        
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    response = requests.post(f'https://{api_base}/v1/chat/completions', headers=headers, json=request_data)
    try:
        response_json = response.json()
        response_content = response_json['choices'][0]['message']['content']
        
        # Cache the response
        cache_manager.cache_response('openai', request_data, response_content)
        
        return response_content
    except Exception as e:
        print(f"Error in ask_openai_for_json: {str(e)}")
        return None

def common_ask_for_json(prompt):
    if os.environ.get('AZURE_OR_OPENAI') == 'AZURE':
        return azure_openai_json(prompt)
    else:
        return ask_openai_for_json(prompt)

def ask_claude(prompt):
    model = os.environ.get('CLAUDE_MODEL', 'claude-3-5-sonnet-20240620')
    api_key = os.environ.get('OPENAI_API_KEY')
    api_base = os.environ.get('OPENAI_API_BASE', 'https://apix.ai-gaochao.cn')
    
    # Prepare request data
    request_data = {
        'model': model,
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ]
    }
    
    # Check cache first
    cached_response = cache_manager.get_cached_response('claude', request_data)
    if cached_response:
        return cached_response

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    try:
        response = requests.post(f'https://{api_base}/v1/chat/completions', 
                               headers=headers, 
                               json=request_data)
        response.raise_for_status()
        response_data = response.json()
        response_content = response_data['choices'][0]['message']['content']
        
        # Cache the response
        cache_manager.cache_response('claude', request_data, response_content)
        
        return response_content
    except requests.exceptions.RequestException as e:
        print(f"Claude API调用失败。错误: {str(e)}")
        return ""

def common_ask(prompt):
    model_type = os.environ.get('AZURE_OR_OPENAI', 'CLAUDE')
    if model_type == 'AZURE':
        return azure_openai(prompt)
    elif model_type == 'CLAUDE':
        return ask_claude(prompt)
    elif model_type == 'DEEPSEEK':
        return ask_deepseek_common(prompt)
    else:
        return ask_openai_common(prompt)

def clean_text(text: str) -> str:
    return str(text).replace(" ", "").replace("\n", "").replace("\r", "")

def common_get_embedding(text: str):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    api_base = os.getenv('OPENAI_API_BASE', 'api.openai.com')
    model = os.getenv("PRE_TRAIN_MODEL", "text-embedding-3-large")
    
    # Prepare request data
    request_data = {
        "input": clean_text(text),
        "model": model,
        "encoding_format": "float"
    }
    
    # Check cache first
    cached_response = cache_manager.get_cached_response('openai_embedding', request_data)
    if cached_response:
        return json.loads(cached_response)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(f'https://{api_base}/v1/embeddings', json=request_data, headers=headers)
        response.raise_for_status()
        embedding_data = response.json()
        response_content = embedding_data['data'][0]['embedding']
        
        # Cache the response
        cache_manager.cache_response('openai_embedding', request_data, json.dumps(response_content))
        
        return response_content
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return list(np.zeros(3072))  # 返回长度为3072的全0数组

def common_get_embedding2(text: str):
    api_key = os.getenv('OPENAI_EMBEDDING_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_EMBEDDING_API_KEY environment variable is not set")

    api_base = os.getenv('OPENAI_EMBEDDING_BASE', 'https://ark.cn-beijing.volces.com/api/v3')
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "ep-20241218223410-kwbkm")
    
    # Prepare request data
    request_data = {
        "input": clean_text(text),
        "model": model,
        "encoding_format": "float"
    }
    
    # Check cache first
    cached_response = cache_manager.get_cached_response('custom_embedding', request_data)
    if cached_response:
        return json.loads(cached_response)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(f'https://{api_base}/embeddings', json=request_data, headers=headers)
        response.raise_for_status()
        embedding_data = response.json()
        response_content = embedding_data['data'][0]['embedding']
        
        # Cache the response
        cache_manager.cache_response('custom_embedding', request_data, json.dumps(response_content))
        
        return response_content
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return list(np.zeros(4096))  # 返回长度为4096的全0数组