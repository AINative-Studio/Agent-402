> ## Documentation Index
> Fetch the complete documentation index at: https://developers.circle.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Create wallets

> Creates a new developer-controlled wallet or a batch of wallets within a wallet set, given the target blockchain and wallet name.

**Note:** Each `walletSetId` supports a maximum of 10 million wallets.




## OpenAPI

````yaml openapi/developer-controlled-wallets.yaml post /v1/w3s/developer/wallets
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
  /v1/w3s/developer/wallets:
    post:
      tags:
        - Wallets
      summary: Create wallets
      description: >
        Creates a new developer-controlled wallet or a batch of wallets within a
        wallet set, given the target blockchain and wallet name.


        **Note:** Each `walletSetId` supports a maximum of 10 million wallets.
      operationId: createWallet
      parameters:
        - $ref: '#/components/parameters/XRequestId'
      requestBody:
        $ref: '#/components/requestBodies/CreateWallet'
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Wallets'
          description: >-
            Returns the existing wallet(s) if the idempotency key matches a
            previous successful request.
          headers:
            X-Request-Id:
              $ref: '#/components/headers/XRequestId'
        '201':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Wallets'
          description: Successfully created the wallet(s).
          headers:
            X-Request-Id:
              $ref: '#/components/headers/XRequestId'
        '400':
          $ref: '#/components/responses/BadRequest'
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
    CreateWallet:
      content:
        application/json:
          schema:
            type: object
            required:
              - blockchains
              - entitySecretCiphertext
              - walletSetId
              - idempotencyKey
            properties:
              idempotencyKey:
                $ref: '#/components/schemas/IdempotencyKey'
              accountType:
                $ref: '#/components/schemas/AccountType'
              blockchains:
                type: array
                items:
                  $ref: '#/components/schemas/Blockchain'
                description: Blockchain(s) the requested wallets will be created on.
              count:
                type: integer
                description: >-
                  Number of wallets that will be created per specified
                  blockchain.
                example: 2
                maximum: 200
                minimum: 1
              entitySecretCiphertext:
                $ref: '#/components/schemas/EntitySecretCiphertext'
              metadata:
                type: array
                items:
                  $ref: '#/components/schemas/WalletMetadata'
                description: >-
                  List of metadata fields to associate with the corresponding
                  wallet. If count is specified, the amount of items in the
                  array should match the count field.
              walletSetId:
                $ref: '#/components/schemas/Id'
      description: Schema for the request payload to create a new wallet.
      required: true
  schemas:
    Wallets:
      title: WalletsResponse
      type: object
      required:
        - data
      properties:
        data:
          type: object
          required:
            - wallets
          properties:
            wallets:
              type: array
              items:
                oneOf:
                  - $ref: '#/components/schemas/EOAWallet'
                  - $ref: '#/components/schemas/SCAWallet'
                discriminator:
                  propertyName: accountType
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
    AccountType:
      type: string
      description: >
        An account can be a Smart Contract Account (SCA) or an Externally Owned
        Account (EOA). To learn more, see the [account types
        guide](https://developers.circle.com/wallets/account-types).


        If an account type is not specified during the creation of a wallet, it
        defaults to `EOA` (Externally Owned Account). Note that Solana and Aptos
        don't support Smart Contract Account (SCA).
      enum:
        - SCA
        - EOA
    Blockchain:
      type: string
      description: >-
        The blockchain network that the resource is to be created on or is
        currently on.
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
        - NEAR
        - NEAR-TESTNET
        - EVM
        - EVM-TESTNET
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
    EntitySecretCiphertext:
      type: string
      description: >
        A base64 string expression of the entity secret ciphertext. The entity
        secret should be encrypted by the entity public key. Circle mandates
        that the entity secret ciphertext is unique for each API request.
      format: byte
      example: >-
        M8OAwbJ8rMsPd8+NT4xRDBDJSNqUKAvJeWPyuwZSlVXgRucogAlBxjvjIw4nsKeJ4hejjlpmyaaJrusHm6zsvy4BLuL1an3dYn3wORjYf3sU4QN9Rdk9OJxZvE5hDNPq7okucvb1eElxPVREZvr4ew7sh4ktmwDrwWFUYwKoly4fEzxYI9zvVpCY9xPSgkA5m3u1/P2vMYZ0QFtn8lRZxCuTyc4wRLpT9TOaK46CEXCakmAYaYWnLkl18QXOSY6FhCbGm+zQ2Uu4cUPU/bqjIyQIB80ut3drInDzysQLE/FJjcJW9+q+E75LKGKnrp2zCg/Xv3TEvru9a2A0vd7InZ9kNuxnPPFc1JSO7BT2TPP89YcLO0OmtRiGoXPlYzXuNIfUsVQ5/FW9FPp4qp+iMPrAidsjQrskHPxhW92GeezLpOSkUl7lAWQoioYED979mqGfzNIZTF5Ob6fJifboiwhOab6sAKnxmvWjgFnW/bZ5a8xkzgPc4RHpIejot1Q7fpT+67eA+DVxvUqakJI6t3iEaZTNITCSU2Cfj1oyCQfrZGf9tauW49rO1zYHKoV4z9ylymOWtCUk641iyxwFCNSW47CDsc0M8iI4J6JqsNMpQuR9sdWVhROi5yn9UR7ac7pizB3dFmc0/qjtTRoYStaaSEYg3L5woALv5kAA2j4=
    WalletMetadata:
      type: object
      properties:
        name:
          $ref: '#/components/schemas/Name'
        refId:
          $ref: '#/components/schemas/ReferenceId'
    Id:
      type: string
      format: uuid
      description: System-generated unique identifier of the resource.
      example: c4d1da72-111e-4d52-bdbf-2e74a2d803d5
    EOAWallet:
      title: EOAWallet
      allOf:
        - $ref: '#/components/schemas/Wallet'
        - type: object
          required:
            - accountType
          properties:
            accountType:
              type: string
              description: >
                An account can be a Smart Contract Account (SCA) or an
                Externally Owned Account (EOA). To learn more, see the [account
                types
                guide](https://developers.circle.com/wallets/account-types).


                If an account type is not specified during the creation of a
                wallet, it defaults to `EOA` (Externally Owned Account). Note
                that Solana and Aptos don't support Smart Contract Account
                (SCA).
              enum:
                - EOA
    SCAWallet:
      title: SCAWallet
      allOf:
        - $ref: '#/components/schemas/Wallet'
        - type: object
          required:
            - accountType
            - scaCore
          properties:
            accountType:
              type: string
              description: >
                An account can be a Smart Contract Account (SCA) or an
                Externally Owned Account (EOA). To learn more, see the [account
                types
                guide](https://developers.circle.com/wallets/account-types).


                If an account type is not specified during the creation of a
                wallet, it defaults to `EOA` (Externally Owned Account). Note
                that Solana and Aptos don't support Smart Contract Account
                (SCA).
              enum:
                - SCA
            scaCore:
              $ref: '#/components/schemas/ScaCore'
    Name:
      type: string
      description: Name or description associated with the wallet or walletSet.
    ReferenceId:
      type: string
      description: Reference or description used to identify the object.
      example: custom_ref_id
    Wallet:
      type: object
      required:
        - id
        - state
        - walletSetId
        - custodyType
        - address
        - blockchain
        - createDate
        - updateDate
      properties:
        id:
          $ref: '#/components/schemas/Id'
        address:
          $ref: '#/components/schemas/Address'
        blockchain:
          $ref: '#/components/schemas/Blockchain'
        createDate:
          $ref: '#/components/schemas/CreateDate'
        updateDate:
          $ref: '#/components/schemas/UpdateDate'
        custodyType:
          $ref: '#/components/schemas/CustodyType'
        name:
          $ref: '#/components/schemas/Name'
        refId:
          $ref: '#/components/schemas/ReferenceId'
        state:
          $ref: '#/components/schemas/WalletState'
        userId:
          $ref: '#/components/schemas/ExternalUserId'
        walletSetId:
          $ref: '#/components/schemas/Id'
        initialPublicKey:
          $ref: '#/components/schemas/InitialPublicKey'
    ScaCore:
      type: string
      description: >-
        SCAs have different versions, each with unique functionality. `SCACore`
        displays the version of the SCA being created. For a list of supported
        versions, refer to the developer documentation.
      enum:
        - circle_4337_v1
        - circle_6900_singleowner_v1
        - circle_6900_singleowner_v2
        - circle_6900_singleowner_v3
      example: circle_6900_singleowner_v2
    Address:
      title: Address
      description: >
        Blockchain generated unique identifier, associated with wallet
        (account), smart contract or other blockchain objects.
      type: string
      example: '0xca9142d0b9804ef5e239d3bc1c7aa0d1c74e7350'
    CreateDate:
      type: string
      format: date-time
      description: Date and time the resource was created, in ISO-8601 UTC format.
      example: '2023-01-01T12:04:05Z'
    UpdateDate:
      type: string
      format: date-time
      description: Date and time the resource was last updated, in ISO-8601 UTC format.
      example: '2023-01-01T12:04:05Z'
    CustodyType:
      type: string
      description: >
        Describes who controls the digital assets in a wallet: either the
        end-user or the developer.
      enum:
        - DEVELOPER
        - ENDUSER
    WalletState:
      type: string
      description: This enum describes the current state of the wallet.
      enum:
        - LIVE
        - FROZEN
      example: LIVE
    ExternalUserId:
      type: string
      description: Unique system generated identifier for the user.
      example: ext_user_id_1
      maxLength: 50
      minLength: 5
    InitialPublicKey:
      type: string
      description: >-
        For NEAR blockchains only, the originally assigned public key of a
        wallet at the time of its creation.
      example: 3eQoJ3ex6uWX3R8F1THF6Y6oBQwPYpF1X9HBM1gjqw7w
  headers:
    XRequestId:
      description: >
        Developer-provided header parameter or Circle-generated universally
        unique identifier (UUID v4). Useful for identifying a specific request
        when communicating with Circle Support.
      schema:
        $ref: '#/components/schemas/XRequestId'
  responses:
    BadRequest:
      content:
        application/json:
          schema:
            type: object
            title: BadRequestResponse
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
              code: 400
              message: Bad request.
      description: Request cannot be processed due to a client error.
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