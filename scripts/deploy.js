const { ethers } = require("hardhat");

async function main() {
  const DevicePassport = await ethers.getContractFactory("DevicePassport");
  console.log("Deploying DevicePassport to Polygon Amoy...");

  const contract = await DevicePassport.deploy();
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
