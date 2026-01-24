> ## Documentation Index
> Fetch the complete documentation index at: https://developers.circle.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Create a new wallet set

> Creates a new developer-controlled wallet set.

**Note:** A developer account can create up to 1,000 wallet sets, with each set supporting up to 10 million wallets.
To ensure EVM wallets are created with the same address across chains, see [Unified Wallet Addressing on EVM Chains](/w3s/unified-wallet-addressing-evm).




## OpenAPI

````yaml openapi/developer-controlled-wallets.yaml post /v1/w3s/developer/walletSets
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
  /v1/w3s/developer/walletSets:
    post:
      tags:
        - Wallet Sets
      summary: Create a new wallet set
      description: >
        Creates a new developer-controlled wallet set.


        **Note:** A developer account can create up to 1,000 wallet sets, with
        each set supporting up to 10 million wallets.

        To ensure EVM wallets are created with the same address across chains,
        see [Unified Wallet Addressing on EVM
        Chains](/w3s/unified-wallet-addressing-evm).
      operationId: createWalletSet
      parameters:
        - $ref: '#/components/parameters/XRequestId'
      requestBody:
        $ref: '#/components/requestBodies/CreateWalletSet'
      responses:
        '200':
          description: Wallet set already exists.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WalletSetResponse'
          headers:
            X-Request-Id:
              $ref: '#/components/headers/XRequestId'
        '201':
          description: Successfully created wallet set.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WalletSetResponse'
          headers:
            X-Request-Id:
              $ref: '#/components/headers/XRequestId'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/NotAuthorized'
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
    CreateWalletSet:
      content:
        application/json:
          schema:
            type: object
            required:
              - entitySecretCiphertext
              - idempotencyKey
            properties:
              entitySecretCiphertext:
                $ref: '#/components/schemas/EntitySecretCiphertext'
              idempotencyKey:
                $ref: '#/components/schemas/IdempotencyKey'
              name:
                $ref: '#/components/schemas/Name'
      required: true
      description: Schema for the request payload to create a new wallet set.
  schemas:
    WalletSetResponse:
      title: WalletSetResponse
      type: object
      required:
        - data
      properties:
        data:
          type: object
          required:
            - walletSet
          properties:
            walletSet:
              oneOf:
                - $ref: '#/components/schemas/DeveloperWalletSet'
                - $ref: '#/components/schemas/EndUserWalletSet'
              discriminator:
                propertyName: custodyType
    XRequestId:
      type: string
      description: >-
        A unique identifier, which can be helpful for identifying a request when
        communicating with Circle support.
      example: 2adba88e-9d63-44bc-b975-9b6ae3440dde
    EntitySecretCiphertext:
      type: string
      description: >
        A base64 string expression of the entity secret ciphertext. The entity
        secret should be encrypted by the entity public key. Circle mandates
        that the entity secret ciphertext is unique for each API request.
      format: byte
      example: >-
        M8OAwbJ8rMsPd8+NT4xRDBDJSNqUKAvJeWPyuwZSlVXgRucogAlBxjvjIw4nsKeJ4hejjlpmyaaJrusHm6zsvy4BLuL1an3dYn3wORjYf3sU4QN9Rdk9OJxZvE5hDNPq7okucvb1eElxPVREZvr4ew7sh4ktmwDrwWFUYwKoly4fEzxYI9zvVpCY9xPSgkA5m3u1/P2vMYZ0QFtn8lRZxCuTyc4wRLpT9TOaK46CEXCakmAYaYWnLkl18QXOSY6FhCbGm+zQ2Uu4cUPU/bqjIyQIB80ut3drInDzysQLE/FJjcJW9+q+E75LKGKnrp2zCg/Xv3TEvru9a2A0vd7InZ9kNuxnPPFc1JSO7BT2TPP89YcLO0OmtRiGoXPlYzXuNIfUsVQ5/FW9FPp4qp+iMPrAidsjQrskHPxhW92GeezLpOSkUl7lAWQoioYED979mqGfzNIZTF5Ob6fJifboiwhOab6sAKnxmvWjgFnW/bZ5a8xkzgPc4RHpIejot1Q7fpT+67eA+DVxvUqakJI6t3iEaZTNITCSU2Cfj1oyCQfrZGf9tauW49rO1zYHKoV4z9ylymOWtCUk641iyxwFCNSW47CDsc0M8iI4J6JqsNMpQuR9sdWVhROi5yn9UR7ac7pizB3dFmc0/qjtTRoYStaaSEYg3L5woALv5kAA2j4=
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
    Name:
      type: string
      description: Name or description associated with the wallet or walletSet.
    DeveloperWalletSet:
      allOf:
        - $ref: '#/components/schemas/WalletSet'
        - type: object
          required:
            - custodyType
          properties:
            custodyType:
              type: string
              enum:
                - DEVELOPER
    EndUserWalletSet:
      allOf:
        - $ref: '#/components/schemas/WalletSet'
        - type: object
          required:
            - custodyType
            - userId
          properties:
            custodyType:
              type: string
              enum:
                - ENDUSER
            userId:
              $ref: '#/components/schemas/ExternalUserId'
    WalletSet:
      type: object
      required:
        - id
        - custodyType
        - createDate
        - updateDate
      properties:
        id:
          $ref: '#/components/schemas/Id'
        createDate:
          $ref: '#/components/schemas/CreateDate'
        updateDate:
          $ref: '#/components/schemas/UpdateDate'
    ExternalUserId:
      type: string
      description: Unique system generated identifier for the user.
      example: ext_user_id_1
      maxLength: 50
      minLength: 5
    Id:
      type: string
      format: uuid
      description: System-generated unique identifier of the resource.
      example: c4d1da72-111e-4d52-bdbf-2e74a2d803d5
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