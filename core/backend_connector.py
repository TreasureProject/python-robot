# agent/core/backend_connector.py

import httpx
from typing import Optional
from eth_account import Account
from x402.clients.httpx import x402HttpxClient
from x402.clients.base import decode_x_payment_response, x402Client


def default_x402_selector(accepts, network_filter=None, scheme_filter=None, max_value=None):
    """
    Default selector for x402 payments.
    Always selects network 'base-sepolia'.
    """
    _ = network_filter  # ignore parameter
    return x402Client.default_payment_requirements_selector(
        accepts,
        network_filter="base-sepolia",
        scheme_filter=scheme_filter,
        max_value=max_value,
    )


class BackendConnector:
    """
    Backend connector for normal HTTP requests and x402 payments.
    No persistent sessions — everything is on-demand.
    """

    def __init__(self, base_url: str, x402_mnemonic: Optional[str] = None, default_timeout: float = 600.0):
        self.base_url = base_url.rstrip("/")
        self.account: Optional[Account] = None
        self.default_timeout = default_timeout

        if x402_mnemonic:
            # Enable HD wallet features to use mnemonic
            Account.enable_unaudited_hdwallet_features()
            self.account = Account.from_mnemonic(x402_mnemonic)

    async def send_request(
        self, path: str, method: str = "GET", json_body: Optional[dict] = None
    ) -> httpx.Response:
        """
        Normal HTTP request.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        async with httpx.AsyncClient() as client:
            response = await client.request(method=method, url=url, json=json_body)
            return response

    async def send_x402_request(
        self, path: str, method: str = "GET", json_body: Optional[dict] = None, timeout: Optional[float] = None
    ):
        """
        HTTP request with automatic x402 payment using default selector.
        Returns (response, payment_info)
        
        Args:
            path: API endpoint path
            method: HTTP method (GET, POST, etc.)
            json_body: JSON body for the request
            timeout: Request timeout in seconds (default: self.default_timeout)
        """
        if not self.account:
            raise ValueError("x402 mnemonic (seed phrase) is required for x402 requests.")

        url = f"{self.base_url}/{path.lstrip('/')}"
        request_timeout = timeout if timeout is not None else self.default_timeout

        async with x402HttpxClient(
            account=self.account,
            base_url=self.base_url,
            payment_requirements_selector=default_x402_selector,
            timeout=httpx.Timeout(request_timeout, connect=10.0),
        ) as client:

            response = await client.request(method=method, url=url, json=json_body)

            payment_info = None
            if "X-Payment-Response" in response.headers:
                payment_info = decode_x_payment_response(
                    response.headers["X-Payment-Response"]
                )

            return response, payment_info

    async def chat(
        self,
        message: str,
        sender_name: str = "User",
        agent_name: str = "0xdacd02dd0ce8a923ad26d4c49bb94ece09306c3e",
        chat_history: list = None,
        currency: str = "USDC",
        timeout: float = 120.0,
    ):
        """
        Sends a chat message to the AI Frens API with x402 payment.
        
        Args:
            message: The chat message text
            sender_name: Name of the sender (default: "User")
            agent_name: Agent token ID (default: Wiz token ID from example)
            chat_history: List of previous chat messages (default: empty list)
            currency: Payment currency (default: "USDC")
            timeout: Request timeout in seconds (default: 120.0 for LLM responses)
        
        Returns:
            dict with 'paymentResponse' and 'response' (chat response)
        """
        if not self.account:
            raise ValueError("x402 mnemonic (seed phrase) is required for chat requests.")

        sender_id = self.account.address
        chat_id = f"{sender_id}-{agent_name}"
        
        chat_input = {
            "message": message,
            "senderName": sender_name,
            "senderId": sender_id,
            "chatHistory": chat_history or [],
            "agentName": agent_name,
            "chatId": chat_id,
            "isGroupChat": False,
            "currency": currency,
        }

        response, payment_info = await self.send_x402_request(
            path="/chat",
            method="POST",
            json_body=chat_input,
            timeout=timeout,
        )

        response_data = None
        if response.status_code == 200:
            try:
                response_data = response.json()
            except Exception as e:
                print(f"[CHAT] Failed to parse response JSON: {e}")
                response_data = {"error": f"Failed to parse response: {str(e)}"}
        else:
            try:
                error_data = response.json()
                response_data = error_data
            except:
                response_data = {"error": f"HTTP {response.status_code}: {response.text}"}

        return {
            "paymentResponse": payment_info,
            "response": response_data,
        }