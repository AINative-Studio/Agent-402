> ## Documentation Index
> Fetch the complete documentation index at: https://developers.circle.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Entity Secret Management

## What is an Entity Secret?

The Entity Secret is a 32-byte private key designed to secure your
developer-controlled wallets. It acts as your secret password, your personalized
cryptographic stamp, known only to you.

Circle's platform does not store the Entity Secret. This ensures that only you
can invoke private keys, maintaining complete control. It is therefore your
responsibility to safeguard this secret.

<Accordion title="Video Tutorial: Generate and Encrypt an Entity Secret">
  Watch this video to help you build alongside our docs. Learn how to generate
  an Entity Secret, Fetch your Entity's Public Key, generate the Entity Secret
  Ciphertext, and register the Entity Secret Ciphertext in the developer
  console.

  <iframe src="https://fast.wistia.net/embed/iframe/aupti5g6vf?seo=true&videoFoam=true" title="Video Tutorial: Generate and Encrypt an Entity Secret" height="100%" width="100%" style={{ maxWidth: '800px', aspectRatio: '16/9' }} />
</Accordion>

## What is an Entity Secret Ciphertext?

The Entity Secret <Tooltip tip="refers to the encrypted form of plain text that is transformed using cryptographic algorithms. It is the result of applying encryption techniques to the original message, making it unreadable to anyone without the decryption key or appropriate knowledge. Ciphertext acts as a security measure, ensuring the confidentiality and integrity of sensitive information during communication or storage. Reverse operations, such as decryption, are required to convert ciphertext back into the original readable plaintext.">Ciphertext</Tooltip> is a
<Tooltip tip="is a widely used asymmetric encryption algorithm. RSA encryption involves two keys, a public key and a private key. The public key is used for encryption, while the private key is used for decryption. The keys are mathematically related, but it is computationally infeasible to determine the private key from the public key. RSA encryption is widely used for secure communication, digital signatures, and key exchange protocols. Its security relies on the difficulty of factoring large numbers into prime factors, making it resistant to attacks from classical and quantum computers when sufficiently large keys are used.">RSA encryption</Tooltip> token generated from your Entity Secret and
Circle's public key. This asymmetrically encrypted value is sent in API requests
like wallet creation or transaction initiation to ensure critical actions are
secure. This process enables secure usage of the Entity Secret, to ensure it
cannot be easily accessed or misused.

## How to Create and Register the Entity Secret

There are three options to register your Entity Secret:

1. Use one of our server-side SDKs to generate the Entity Secret, encrypt it,
   and register it
2. Generate the Entity Secret yourself by
   [using Standard Libraries or CLI tools](https://github.com/circlefin/w3s-entity-secret-sample-code),
   then use the SDK to encrypt it and register it
3. Generate the Entity Secret yourself by
   [using Standard Libraries or CLI tools](https://github.com/circlefin/w3s-entity-secret-sample-code),
   encrypt it with the Entity public key to generate the Entity Secret
   Ciphertext, then register it in the Circle Console.

<Note>
  Option 1 provides the most streamlined experience since our SDK does the heavy
  lifting to manage the Entity Secret registration process. However, depending
  on your needs, you can selectively use Option 2 or 3 to generate and encrypt
  the entity secret directly.
</Note>

The process to register your entity secret and create your first developer
wallet is best laid out in our
[Register Your Entity Secret](/wallets/dev-controlled/register-entity-secret)
QuickStart and
[Create Your First Developer-Controlled Wallet](/wallets/dev-controlled/create-your-first-wallet)
Interactive Quickstart guides.

**Note:** For any of the options above it is important to create a recovery file
to ensure you can still have access to your funds in case you lose your entity
secret. Option 1 above has this feature built-in already in our SDKs.

## APIs Requiring Entity Secret Ciphertext

| Summary                           | API                                                                                                                                                     |
| :-------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Create a new wallet set           | [`POST /developer/walletSets`](/api-reference/wallets/developer-controlled-wallets/create-wallet-set)                                                   |
| Create wallets                    | [`POST /developer/wallets`](/api-reference/wallets/developer-controlled-wallets/create-wallet)                                                          |
| Create a transfer transaction     | [`POST /developer/transactions/transfer`](/api-reference/wallets/developer-controlled-wallets/create-developer-transaction-transfer)                    |
| Accelerate a transaction          | [`POST /developer/transactions/{id}/accelerate`](/api-reference/wallets/developer-controlled-wallets/create-developer-transaction-accelerate)           |
| Cancel a transaction              | [`POST /transactions/{id}/cancel`](/api-reference/wallets/developer-controlled-wallets/create-developer-transaction-cancel)                             |
| Execute a contract transaction    | [`POST /developer/transactions/contractExecution`](/api-reference/wallets/developer-controlled-wallets/create-developer-transaction-contract-execution) |
| Deploy a contract                 | [`POST /contracts/deploy`](/api-reference/contracts/smart-contract-platform/deploy-contract)                                                            |
| Deploy a contract from a template | [`POST /templates/{id}/deploy`](/api-reference/contracts/smart-contract-platform/deploy-contract-template)                                              |

## How to Rotate the Entity Secret

Periodic rotation of the Entity Secret enhances the overall security of
developer-controlled wallets. Developers can initiate the Entity Secret rotation
process when they possess the existing Entity Secret. To perform rotation, you
will provide the system with the current Entity's Secret Ciphertext and the
newly created one. The system verifies the authenticity of the provided
information before updating the Entity Secret. This process ensures that the
Entity Secret remains fresh, reducing the risk of potential vulnerabilities
associated with long-term use of the same secret.

**Additional Notes:**

* Entity Secret rotation takes immediate effect, rendering the old Entity Secret
  deprecated. As a result, ongoing API requests using the old Entity Secret will
  fail. Make sure to complete existing API requests before rotation, or
  reinitialize them following the entity secret rotation.
* The existing Entity Secret Ciphertext does not need to be the same as the one
  registered as long as it is derived from the existing Entity Secret (encrypted
  and encoded). The newly created Entity Secret Ciphertext should be derived
  from a newly generated 32-byte entity secret to ensure security.
* When the newly created Entity Secret is registered the previous recovery file
  will be deprecated, and a renewed recovery file can be downloaded for
  resetting the Entity Secret.

## How to Reset the Entity Secret

Developers can initiate the Entity Secret reset process when an Entity Secret is
compromised or lost. To ensure the security of the reset operation, developers
need to upload the recovery file for authentication. After uploading the
recovery file and entering the newly created Entity Secret Ciphertext into the
system, the Entity Secret is reset, and a renewed recovery file can be
downloaded

**Additional Notes:**

* Entity Secret reset takes immediate effect, rendering the old Entity Secret
  deprecated. As a result, ongoing API requests using the old Entity Secret will
  fail. Make sure to complete existing API requests before reset, or
  reinitializing them following the Entity Secret reset.

<Warning>
  If both the Entity Secret and the recovery file are lost, you cannot create new
  developer-controlled wallets or initiate transactions from existing ones. Store
  both the Entity Secret string and the recovery file safely.
</Warning>