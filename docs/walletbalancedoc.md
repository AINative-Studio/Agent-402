> ## Documentation Index
> Fetch the complete documentation index at: https://developers.circle.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Get token balance for a wallet

> Fetches the digital asset balance for a single developer-controlled wallet using its unique identifier.

**Note**: On Aptos, this endpoint only returns balances for tokens stored in primary storage. Tokens held in [AIP-21](https://github.com/aptos-labs/aptos-core/releases/tag/aptos-node-v1.5.0) secondary storage are excluded from balance queries and deposit notifications to prevent incorrect or misleading results from secondary storage-based state changes.



## OpenAPI

````yaml openapi/developer-controlled-wallets.yaml get /v1/w3s/wallets/{id}/balances
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
  /v1/w3s/wallets/{id}/balances:
    get:
      tags:
        - Wallets
      summary: Get token balance for a wallet
      description: >-
        Fetches the digital asset balance for a single developer-controlled
        wallet using its unique identifier.


        **Note**: On Aptos, this endpoint only returns balances for tokens
        stored in primary storage. Tokens held in
        [AIP-21](https://github.com/aptos-labs/aptos-core/releases/tag/aptos-node-v1.5.0)
        secondary storage are excluded from balance queries and deposit
        notifications to prevent incorrect or misleading results from secondary
        storage-based state changes.
      operationId: listWalletBalance
      parameters:
        - description: Wallet ID
          in: path
          name: id
          required: true
          schema:
            type: string
        - $ref: '#/components/parameters/IncludeAll'
        - $ref: '#/components/parameters/TokenName'
        - $ref: '#/components/parameters/TokenAddress'
        - $ref: '#/components/parameters/TokenStandard'
        - $ref: '#/components/parameters/PageBefore'
        - $ref: '#/components/parameters/PageAfter'
        - $ref: '#/components/parameters/PageSize'
        - $ref: '#/components/parameters/XRequestId'
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Balances'
          description: Success
          headers:
            X-Request-Id:
              $ref: '#/components/headers/XRequestId'
            Link:
              $ref: '#/components/headers/PaginationLink'
        '400':
          $ref: '#/components/responses/DefaultError'
        '404':
          $ref: '#/components/responses/NotFound'
      security:
        - BearerAuth: []
components:
  parameters:
    IncludeAll:
      name: includeAll
      description: Return all recourses with monitored and non-monitored tokens.
      in: query
      required: false
      schema:
        type: boolean
        example: true
    TokenName:
      name: name
      description: Filter by token name.
      in: query
      schema:
        type: string
    TokenAddress:
      name: tokenAddress
      description: Filter by token address.
      in: query
      schema:
        $ref: '#/components/schemas/Address'
    TokenStandard:
      name: standard
      description: >-
        Filter by the token standard. ERC20/ERC721/ERC1155 are the standards for
        EVM chains,
        Fungible/FungibleAsset/NonFungible/NonFungibleEdition/ProgrammableNonFungible/ProgrammableNonFungibleEdition
        are the standards for the Solana chain, FungibleAsset is the standard
        for the Aptos chain.
      in: query
      schema:
        $ref: '#/components/schemas/TokenStandard'
    PageBefore:
      name: pageBefore
      description: >
        A collection ID value used for pagination.


        It marks the exclusive end of a page. When provided, the collection
        resource will return the next n items before

        the id, with n being specified by pageSize.


        The items will be returned in the natural order of the collection.


        The resource will return the first page if neither pageAfter nor
        pageBefore are specified. 


        SHOULD NOT be used in conjunction with pageAfter.
      in: query
      schema:
        type: string
        format: uuid
    PageAfter:
      name: pageAfter
      description: >
        A collection ID value used for pagination.


        It marks the exclusive begin of a page. When provided, the collection
        resource will return the next n items after

        the id, with n being specified by pageSize.


        The items will be returned in the natural order of the collection.


        The resource will return the first page if neither pageAfter nor
        pageBefore are specified.


        SHOULD NOT be used in conjunction with pageBefore.
      in: query
      schema:
        type: string
        format: uuid
    PageSize:
      name: pageSize
      description: >
        Limits the number of items to be returned.


        Some collections have a strict upper bound that will disregard this
        value. In case the specified value is higher

        than the allowed limit, the collection limit will be used.


        If avoided, the collection will determine the page size itself.
      in: query
      schema:
        type: integer
        default: 10
        maximum: 50
        minimum: 1
    XRequestId:
      name: X-Request-Id
      description: >-
        Developer-provided parameter used to identify this request. Useful when
        communicating with Circle Support.
      in: header
      schema:
        $ref: '#/components/schemas/XRequestId'
  schemas:
    Balances:
      title: BalancesResponse
      type: object
      required:
        - data
      properties:
        data:
          type: object
          properties:
            tokenBalances:
              description: List of token balances for each token on the wallet(s).
              type: array
              items:
                $ref: '#/components/schemas/Balance'
    Address:
      title: Address
      description: >
        Blockchain generated unique identifier, associated with wallet
        (account), smart contract or other blockchain objects.
      type: string
      example: '0xca9142d0b9804ef5e239d3bc1c7aa0d1c74e7350'
    TokenStandard:
      title: TokenStandard
      type: string
      enum:
        - ERC20
        - ERC721
        - ERC1155
        - Fungible
        - FungibleAsset
        - NonFungible
        - NonFungibleEdition
        - ProgrammableNonFungible
        - ProgrammableNonFungibleEdition
    XRequestId:
      type: string
      description: >-
        A unique identifier, which can be helpful for identifying a request when
        communicating with Circle support.
      example: 2adba88e-9d63-44bc-b975-9b6ae3440dde
    Balance:
      title: Balance
      type: object
      required:
        - token
        - updateDate
        - amount
      properties:
        amount:
          type: string
          description: Token balance for each token in the wallet.
          example: '6.62607015'
        token:
          $ref: '#/components/schemas/Token'
        updateDate:
          $ref: '#/components/schemas/UpdateDate'
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
    Token:
      title: Token
      type: object
      required:
        - id
        - blockchain
        - isNative
        - createDate
        - updateDate
      properties:
        id:
          $ref: '#/components/schemas/Id'
        name:
          type: string
          description: Blockchain name of the specified token.
        standard:
          $ref: '#/components/schemas/TokenStandard'
        blockchain:
          $ref: '#/components/schemas/Blockchain'
        decimals:
          type: integer
          description: Number of decimal places shown in the token amount.
        isNative:
          type: boolean
          description: >-
            Defines if the token is a native token of the specified blockchain.
            If TRUE, the token is a native token.
        symbol:
          type: string
          description: Blockchain symbol of the specified token.
        tokenAddress:
          $ref: '#/components/schemas/Address'
        updateDate:
          $ref: '#/components/schemas/UpdateDate'
        createDate:
          $ref: '#/components/schemas/CreateDate'
    UpdateDate:
      type: string
      format: date-time
      description: Date and time the resource was last updated, in ISO-8601 UTC format.
      example: '2023-01-01T12:04:05Z'
    Id:
      type: string
      format: uuid
      description: System-generated unique identifier of the resource.
      example: c4d1da72-111e-4d52-bdbf-2e74a2d803d5
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
    CreateDate:
      type: string
      format: date-time
      description: Date and time the resource was created, in ISO-8601 UTC format.
      example: '2023-01-01T12:04:05Z'
  headers:
    XRequestId:
      description: >
        Developer-provided header parameter or Circle-generated universally
        unique identifier (UUID v4). Useful for identifying a specific request
        when communicating with Circle Support.
      schema:
        $ref: '#/components/schemas/XRequestId'
    PaginationLink:
      description: >
        Pagination cursor information. Format includes the following link
        relations: - self: URL pointing to the current page. - first: URL
        pointing to the first page. - next: URL pointing to the next page
        (omitted on the last page). - prev: URL pointing to the previous page
        (omitted on the first page).

        It's important to form calls with Link header values instead of
        constructing your own URLs.
      schema:
        type: string
        example: >-
          <https://api.circle.com/v1/w3s/wallets?pageAfter=32d1b923-c30d-58de-a42e-157bf7148b85&pageSize=2>;
          rel="next"
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