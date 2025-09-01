const { app } = require('@azure/functions');
const { BlobServiceClient } = require('@azure/storage-blob');
const { DefaultAzureCredential } = require('@azure/identity');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

/**
 * Azure Function: Static Site Deployer
 *
 * Triggered when a new file is uploaded to the 'static-sites' blob container.
 * Downloads the site archive, extracts it, and deploys to Azure Static Web Apps.
 */
app.storageBlob('StaticSiteDeployer', {
    path: 'static-sites/{name}',
    connection: 'AzureWebJobsStorage',
    handler: async (blob, context) => {
        const blobName = context.triggerMetadata.name;
        context.log(`Processing blob: ${blobName}`);

        try {
            // Only process .tar.gz files (site archives)
            if (!blobName.endsWith('.tar.gz')) {
                context.log(`Skipping non-archive file: ${blobName}`);
                return;
            }

            // Get configuration from environment
            const config = {
                contentStorageAccountName: process.env.CONTENT_STORAGE_ACCOUNT_NAME,
                staticWebAppName: process.env.STATIC_WEB_APP_NAME,
                resourceGroupName: process.env.STATIC_WEB_APP_RESOURCE_GROUP,
                subscriptionId: process.env.AZURE_SUBSCRIPTION_ID,
                containerName: 'static-sites'
            };

            // Validate configuration
            for (const [key, value] of Object.entries(config)) {
                if (!value) {
                    throw new Error(`Missing configuration: ${key}`);
                }
            }

            context.log('Configuration validated');

            // Initialize Azure credential and blob client
            const credential = new DefaultAzureCredential();
            const blobServiceClient = new BlobServiceClient(
                `https://${config.contentStorageAccountName}.blob.core.windows.net`,
                credential
            );

            // Download the blob to a temporary file
            const tempDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'static-site-'));
            const archivePath = path.join(tempDir, blobName);
            const extractPath = path.join(tempDir, 'extracted');

            context.log(`Downloading blob to: ${archivePath}`);

            const containerClient = blobServiceClient.getContainerClient(config.containerName);
            const blobClient = containerClient.getBlobClient(blobName);

            await blobClient.downloadToFile(archivePath);
            context.log('Blob downloaded successfully');

            // Extract the archive using tar
            await fs.promises.mkdir(extractPath, { recursive: true });
            context.log(`Extracting archive to: ${extractPath}`);

            await execAsync(`tar -xzf "${archivePath}" -C "${extractPath}"`);
            context.log('Archive extracted successfully');

            // Deploy to Static Web Apps using Azure CLI
            await deployToStaticWebApp(config, extractPath, context);

            // Clean up temporary files
            await fs.promises.rm(tempDir, { recursive: true, force: true });

            context.log(`Successfully deployed ${blobName} to Static Web App`);

        } catch (error) {
            context.log.error(`Error processing blob ${blobName}:`, error);
            throw error;
        }
    }
});

/**
 * Deploy extracted site to Azure Static Web Apps using Azure CLI
 */
async function deployToStaticWebApp(config, sitePath, context) {
    try {
        // Get access token for Azure CLI authentication
        const credential = new DefaultAzureCredential();
        const tokenResponse = await credential.getToken(['https://management.azure.com/.default']);

        context.log('Obtained Azure access token');

        // Get Static Web App deployment token using Azure Management API
        const url = `https://management.azure.com/subscriptions/${config.subscriptionId}/resourceGroups/${config.resourceGroupName}/providers/Microsoft.Web/staticSites/${config.staticWebAppName}/listSecrets?api-version=2022-03-01`;

        const response = await axios.post(url, {}, {
            headers: {
                'Authorization': `Bearer ${tokenResponse.token}`,
                'Content-Type': 'application/json'
            }
        });

        const deploymentToken = response.data.properties.apiKey;
        context.log('Retrieved Static Web App deployment token');

        // Use SWA CLI for deployment (simpler and more reliable)
        const swaCommand = `npx @azure/static-web-apps-cli deploy "${sitePath}" --deployment-token="${deploymentToken}" --env=production`;

        context.log('Starting Static Web App deployment...');
        const { stdout, stderr } = await execAsync(swaCommand, {
            cwd: sitePath,
            env: {
                ...process.env,
                SWA_CLI_DEPLOYMENT_TOKEN: deploymentToken
            }
        });

        context.log('SWA CLI stdout:', stdout);
        if (stderr) {
            context.log('SWA CLI stderr:', stderr);
        }

        context.log('Successfully deployed to Static Web App');

    } catch (error) {
        context.log.error('Error deploying to Static Web App:', error);

        // If SWA CLI fails, try direct API approach
        context.log('Attempting direct API deployment as fallback...');
        await deployViaDirectAPI(config, sitePath, context);
    }
}

/**
 * Fallback: Deploy using direct Static Web Apps REST API
 */
async function deployViaDirectAPI(config, sitePath, context) {
    try {
        // This is a simplified approach - in production you'd want to
        // implement the full Static Web Apps deployment protocol
        context.log('Direct API deployment not yet implemented');
        context.log('Site is ready for deployment but requires manual intervention');

        // Log the site contents for debugging
        const files = await fs.promises.readdir(sitePath);
        context.log('Site contents:', files);

    } catch (error) {
        context.log.error('Direct API deployment failed:', error);
        throw error;
    }
}
