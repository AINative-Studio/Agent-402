> ## Documentation Index
> Fetch the complete documentation index at: https://developers.circle.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Create a transfer transaction

> Initiates an on-chain digital asset transfer from a specified developer-controlled wallet.

You must provide either a `walletId` or a `walletAddress` and `blockchain` pair in the request body.




## OpenAPI

````yaml openapi/developer-controlled-wallets.yaml post /v1/w3s/developer/transactions/transfer
openapi: 3.0.3
info:
  version: '1.0'
  title: Developer-Controlled Wallets
  description: Developer-Controlled Wallets API documentation.
servers:
  - url: https://api.circle.com
security:
  - BearerAuth: []
tags:
  - name: Wallet Sets
  - name: Wallets
  - name: Signing
  - name: Transactions
  - name: Token Lookup
paths:
  /v1/w3s/developer/transactions/transfer:
    post:
      tags:
        - Transactions
      summary: Create a transfer transaction
      description: >
        Initiates an on-chain digital asset transfer from a specified
        developer-controlled wallet.


        You must provide either a `walletId` or a `walletAddress` and
        `blockchain` pair in the request body.
      operationId: createDeveloperTransactionTransfer
      parameters:
        - $ref: '#/components/parameters/XRequestId'
      requestBody:
        $ref: '#/components/requestBodies/CreateTransferTransactionForDeveloper'
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: >-
                  #/components/schemas/CreateTransferTransactionForDeveloperResponse
          description: >-
            Returns the existing transaction if the idempotency key matches a
            previous successful request.
          headers:
            X-Request-Id:
              $ref: '#/components/headers/XRequestId'
        '201':
          content:
            application/json:
              schema:
                $ref: >-
                  #/components/schemas/CreateTransferTransactionForDeveloperResponse
          description: A new transaction is created
          headers:
            X-Request-Id:
              $ref: '#/components/headers/XRequestId'
        '400':
          $ref: '#/components/responses/DefaultError'
        '401':
          $ref: '#/components/responses/NotAuthorized'
        '404':
          $ref: '#/components/responses/NotFound'
      security:
        - BearerAuth: []
components:
  parameters:
    XRequestId:
      name: X-Request-Id
      description: >-
        Developer-provided parameter used to identify this request. Useful when
        communicating with Circle Support.
      in: header
      schema:
        $ref: '#/components/schemas/XRequestId'
  requestBodies:
    CreateTransferTransactionForDeveloper:
      content:
        application/json:
          schema:
            title: CreateTransferTransactionForDeveloperRequest
            type: object
            required:
              - destinationAddress
              - entitySecretCiphertext
              - idempotencyKey
            properties:
              idempotencyKey:
                $ref: '#/components/schemas/IdempotencyKey'
              amounts:
                $ref: '#/components/schemas/TransferAmounts-2'
              destinationAddress:
                $ref: '#/components/schemas/Address'
              entitySecretCiphertext:
                $ref: '#/components/schemas/EntitySecretCiphertext'
              feeLevel:
                $ref: '#/components/schemas/FeeLevel'
              gasLimit:
                $ref: '#/components/schemas/GasLimit'
              gasPrice:
                $ref: '#/components/schemas/GasPrice'
              maxFee:
                $ref: '#/components/schemas/MaxFee'
              priorityFee:
                $ref: '#/components/schemas/PriorityFee'
              nftTokenIds:
                $ref: '#/components/schemas/NftTokenIds'
              refId:
                $ref: '#/components/schemas/TransactionReferenceId'
              tokenId:
                $ref: '#/components/schemas/TokenId'
              tokenAddress:
                $ref: '#/components/schemas/TokenAddress'
              blockchain:
                anyOf:
                  - $ref: '#/components/schemas/TransferBlockchain'
                  - $ref: '#/components/schemas/TokenBlockchain'
              walletId:
                $ref: '#/components/schemas/WalletId'
              walletAddress:
                $ref: '#/components/schemas/Address'
      description: Create transaction for developer request
      required: true
  schemas:
    CreateTransferTransactionForDeveloperResponse:
      title: CreateTransferTransactionForDeveloperResponse
      type: object
      properties:
        data:
          type: object
          required:
            - id
            - state
          properties:
            id:
              $ref: '#/components/schemas/Id'
            state:
              $ref: '#/components/schemas/TransactionState'
    XRequestId:
      type: string
      description: >-
        A unique identifier, which can be helpful for identifying a request when
        communicating with Circle support.
      example: 2adba88e-9d63-44bc-b975-9b6ae3440dde
    IdempotencyKey:
      type: string
      description: >-
        Universally unique identifier (UUID v4) idempotency key. This key is
        utilized to ensure exactly-once execution of mutating requests. To
        create a UUIDv4 go to
        [uuidgenerator.net](https://www.uuidgenerator.net). If the same key is
        reused, it will be treated as the same request and the original response
        will be returned.
      example: a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
      format: uuid
    TransferAmounts-2:
      title: TransferAmounts
      type: array
      items:
        type: string
      description: >-
        Transfer amounts in decimal number format, at least one element is
        required for transfer. For ERC721 token transfer, the amounts field is
        required to be ["1"] (array with "1" as the only element).
      example:
        - '6.62607015'
      minItems: 1
    Address:
      title: Address
      description: >
        Blockchain generated unique identifier, associated with wallet
        (account), smart contract or other blockchain objects.
      type: string
      example: '0xca9142d0b9804ef5e239d3bc1c7aa0d1c74e7350'
    EntitySecretCiphertext:
      type: string
      description: >
        A base64 string expression of the entity secret ciphertext. The entity
        secret should be encrypted by the entity public key. Circle mandates
        that the entity secret ciphertext is unique for each API request.
      format: byte
      example: >-
        M8OAwbJ8rMsPd8+NT4xRDBDJSNqUKAvJeWPyuwZSlVXgRucogAlBxjvjIw4nsKeJ4hejjlpmyaaJrusHm6zsvy4BLuL1an3dYn3wORjYf3sU4QN9Rdk9OJxZvE5hDNPq7okucvb1eElxPVREZvr4ew7sh4ktmwDrwWFUYwKoly4fEzxYI9zvVpCY9xPSgkA5m3u1/P2vMYZ0QFtn8lRZxCuTyc4wRLpT9TOaK46CEXCakmAYaYWnLkl18QXOSY6FhCbGm+zQ2Uu4cUPU/bqjIyQIB80ut3drInDzysQLE/FJjcJW9+q+E75LKGKnrp2zCg/Xv3TEvru9a2A0vd7InZ9kNuxnPPFc1JSO7BT2TPP89YcLO0OmtRiGoXPlYzXuNIfUsVQ5/FW9FPp4qp+iMPrAidsjQrskHPxhW92GeezLpOSkUl7lAWQoioYED979mqGfzNIZTF5Ob6fJifboiwhOab6sAKnxmvWjgFnW/bZ5a8xkzgPc4RHpIejot1Q7fpT+67eA+DVxvUqakJI6t3iEaZTNITCSU2Cfj1oyCQfrZGf9tauW49rO1zYHKoV4z9ylymOWtCUk641iyxwFCNSW47CDsc0M8iI4J6JqsNMpQuR9sdWVhROi5yn9UR7ac7pizB3dFmc0/qjtTRoYStaaSEYg3L5woALv5kAA2j4=
    FeeLevel:
      type: string
      enum:
        - LOW
        - MEDIUM
        - HIGH
      example: MEDIUM
      description: >
        A dynamic blockchain fee level setting (`LOW`, `MEDIUM`, or `HIGH`) that
        will be used to pay gas for the transaction. Calculated based on network
        traffic, supply of validators, and demand for transaction verification.
        Cannot be used with `gasPrice`, `priorityFee`, or `maxFee`.

        Estimates for each fee level can be obtained through the [`POST
        /transactions/transfer/estimateFee`](/api-reference/w3s/developer-controlled-wallets/create-transfer-estimate-fee)
        API.
    GasLimit:
      type: string
      description: >
        The maximum units of gas to use for the transaction. Required if
        `feeLevel` is not provided.

        Estimates for this limit can be obtained through the [`POST
        /transactions/transfer/estimateFee`](/api-reference/w3s/developer-controlled-wallets/create-transfer-estimate-fee)
        API.

        GasLimit override (only supported for EOA wallets): Using `gasLimit`
        together with `feeLevel`, the provided `gasLimit` is required to be
        greater or equal to `feeLevel` estimation and will override the
        estimation's gasLimit.
      example: '21000'
    GasPrice:
      type: string
      description: >
        For blockchains without EIP-1559 support, the maximum price of gas, in
        gwei, to use per each unit of gas (see `gasLimit`). Requires `gasLimit`.
        Cannot be used with `feeLevel`, `priorityFee`, or `maxFee`.

        Estimates for this fee can be obtained through the [`POST
        /transactions/transfer/estimateFee`](/api-reference/w3s/developer-controlled-wallets/create-transfer-estimate-fee)
        API.
    MaxFee:
      type: string
      example: '5.935224468'
      description: >
        For blockchains with EIP-1559 support, the maximum price per unit of gas
        (see `gasLimit`), in gwei. Requires `priorityFee`, and `gasLimit` to be
        present. Cannot be used with `feeLevel` or `gasPrice`.

        Estimates for this fee can be obtained through the [`POST
        /transactions/transfer/estimateFee`](/api-reference/w3s/developer-controlled-wallets/create-transfer-estimate-fee)
        API.
    PriorityFee:
      type: string
      example: '1.022783914'
      description: >
        For blockchains with EIP-1559 support, the “tip”, in gwei, to add to the
        base fee as an incentive for validators.

        Please note that the `maxFee` and `gasLimit` parameters are required
        alongside the `priorityFee`. The `feeLevel` and `gasPrice` parameters
        cannot be used with the `priorityFee`. 

        Estimations for this fee can be obtained through the [`POST
        /transactions/transfer/estimateFee`](/api-reference/w3s/developer-controlled-wallets/create-transfer-estimate-fee)
        API.
    NftTokenIds:
      title: NftTokenIds
      type: array
      description: >-
        List of NFT token IDs corresponding with the NFTs to transfer. Batch
        transfers are supported only for ERC-1155 tokens. The length of NFT
        token IDs must match the length of amounts.
      items:
        $ref: '#/components/schemas/NftTokenId'
    TransactionReferenceId:
      type: string
      example: grouptransaction123
      description: Optional reference or description used to identify the transaction.
    TokenId:
      title: TokenId
      type: string
      format: uuid
      description: >-
        System generated identifier of the token. Excluded with `tokenAddress`
        and `tokenBlockchain`.
    TokenAddress:
      title: TokenAddress
      type: string
      description: >-
        Blockchain address of the transferred token. Empty for native tokens.
        Excluded with `tokenId`.
    TransferBlockchain:
      title: TransferBlockchain
      type: string
      description: >
        Blockchain associated with the transfer transaction. Required when
        either of `walletAddress` or `tokenAddress` is provided.
      enum:
        - ETH
        - ETH-SEPOLIA
        - AVAX
        - AVAX-FUJI
        - MATIC
        - MATIC-AMOY
        - SOL
        - SOL-DEVNET
        - ARB
        - ARB-SEPOLIA
        - UNI
        - UNI-SEPOLIA
        - BASE
        - BASE-SEPOLIA
        - OP
        - OP-SEPOLIA
        - APTOS
        - APTOS-TESTNET
        - ARC-TESTNET
        - MONAD
        - MONAD-TESTNET
      example: MATIC-AMOY
    TokenBlockchain:
      title: TokenBlockchain
      type: string
      description: >
        Blockchain of the transferred token. Required if `tokenId` is not
        provided.

        The `blockchain` and `tokenId` fields are mutually exclusive.
      enum:
        - ETH
        - ETH-SEPOLIA
        - AVAX
        - AVAX-FUJI
        - MATIC
        - MATIC-AMOY
        - SOL
        - SOL-DEVNET
        - ARB
        - ARB-SEPOLIA
        - UNI
        - UNI-SEPOLIA
        - BASE
        - BASE-SEPOLIA
        - OP
        - OP-SEPOLIA
        - APTOS
        - APTOS-TESTNET
        - ARC-TESTNET
        - MONAD
        - MONAD-TESTNET
      example: MATIC-AMOY
    WalletId:
      title: WalletId
      type: string
      format: uuid
      description: |
        Unique system generated identifier of the wallet.
        For contract deploys this wallet ID will be used as the source.
      example: a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
    Id:
      type: string
      format: uuid
      description: System-generated unique identifier of the resource.
      example: c4d1da72-111e-4d52-bdbf-2e74a2d803d5
    TransactionState:
      title: TransactionState
      type: string
      description: Current state of the transaction.
      enum:
        - CANCELLED
        - CONFIRMED
        - COMPLETE
        - DENIED
        - FAILED
        - INITIATED
        - CLEARED
        - QUEUED
        - SENT
        - STUCK
    Error:
      title: Error
      type: object
      required:
        - code
        - message
      properties:
        code:
          type: integer
          description: Code that corresponds to the error.
        message:
          type: string
          description: Message that describes the error.
    NftTokenId:
      title: NftTokenId
      type: string
      description: The NFT token ID.
      example: '2'
  headers:
    XRequestId:
      description: >
        Developer-provided header parameter or Circle-generated universally
        unique identifier (UUID v4). Useful for identifying a specific request
        when communicating with Circle Support.
      schema:
        $ref: '#/components/schemas/XRequestId'
  responses:
    DefaultError:
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
      description: Error response
      headers:
        X-Request-Id:
          $ref: '#/components/headers/XRequestId'
    NotAuthorized:
      content:
        application/json:
          schema:
            type: object
            title: NotAuthorizedResponse
            required:
              - code
              - message
            properties:
              code:
                type: integer
                description: Code that corresponds to the error.
              message:
                type: string
                description: Message that describes the error.
            example:
              code: 401
              message: Malformed authorization.
      description: >-
        Request has not been applied because it lacks valid authentication
        credentials.
      headers:
        X-Request-Id:
          $ref: '#/components/headers/XRequestId'
    NotFound:
      content:
        application/json:
          schema:
            type: object
            title: NotFoundResponse
            required:
              - code
              - message
            properties:
              code:
                type: integer
                description: Code that corresponds to the error.
              message:
                type: string
                description: Message that describes the error.
            example:
              code: 404
              message: Not found.
      description: Specified resource was not found.
      headers:
        X-Request-Id:
          $ref: '#/components/headers/XRequestId'
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: PREFIX:ID:SECRET
      description: >-
        Circle's API Keys are formatted in the following structure
        "PREFIX:ID:SECRET". All three parts are requred to make a successful
        request.

````