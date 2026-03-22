const { ethers } = require("hardhat");

function walletAddressFromEnv(privateKeyEnv) {
  const value = process.env[privateKeyEnv];
  if (!value) {
    return ethers.ZeroAddress;
  }

  const normalized = value.startsWith("0x") ? value : `0x${value}`;
  return new ethers.Wallet(normalized).address;
}

async function main() {
  const DevicePassport = await ethers.getContractFactory("DevicePassport");
  console.log("Deploying DevicePassport to Polygon Amoy...");

  const platformWallet = walletAddressFromEnv("PLATFORM_PRIVATE_KEY");
  if (platformWallet === ethers.ZeroAddress) {
    throw new Error("PLATFORM_PRIVATE_KEY is required to deploy the contract.");
  }

  const partnerWallet = walletAddressFromEnv("PARTNER_WALLET_KEY");
  const agentWallet = walletAddressFromEnv("AGENT_WALLET_KEY");
  const recyclerWallet = walletAddressFromEnv("RECYCLER_WALLET_KEY");

  console.log(`Platform wallet : ${platformWallet}`);
  console.log(`Partner wallet  : ${partnerWallet}`);
  console.log(`Agent wallet    : ${agentWallet}`);
  console.log(`Recycler wallet : ${recyclerWallet}`);

  const contract = await DevicePassport.deploy(
    platformWallet,
    partnerWallet,
    agentWallet,
    recyclerWallet
  );
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log(`DevicePassport deployed at: ${address}`);
  console.log("Copy this address into your .env as CONTRACT_ADDRESS");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
