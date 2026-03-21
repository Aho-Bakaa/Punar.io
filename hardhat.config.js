require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.20",
  networks: {
    amoy: {
      url: process.env.POLYGON_RPC_URL || "https://rpc-amoy.polygon.technology",
      accounts: process.env.PLATFORM_PRIVATE_KEY
        ? [`0x${process.env.PLATFORM_PRIVATE_KEY}`]
        : [],
      chainId: 80002,
    },
  },
};
