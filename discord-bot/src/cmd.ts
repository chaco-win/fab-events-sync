import './env.js';
import { Client, GatewayIntentBits, Partials, SlashCommandBuilder, PermissionFlagsBits } from 'discord.js';
import { REST } from '@discordjs/rest';
import { Routes } from 'discord-api-types/v10';
import { db, migrate } from './db.js';

const TOKEN = process.env.DISCORD_TOKEN || '';
const APP_ID = process.env.APP_ID || '';
const GUILD_IDS = (process.env.GUILD_ID || process.env.GUILD_IDS || '')
  .split(',')
  .map(s => s.trim())
  .filter(Boolean);

migrate();

const client = new Client({
  intents: [GatewayIntentBits.Guilds],
  partials: [Partials.Channel]
});

async function registerCommands() {
  if (!TOKEN || !APP_ID) {
    console.warn('Skipping command registration: missing DISCORD_TOKEN or APP_ID');
    return;
  }

  const commands = [
    new SlashCommandBuilder()
      .setName('notify')
      .setDescription('Notification settings')
      .addSubcommand(sc => sc
        .setName('set-channel')
        .setDescription('Set this channel for notifications'))
      .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
      .toJSON()
  ];

  const rest = new REST({ version: '10' }).setToken(TOKEN);

  if (GUILD_IDS.length > 0) {
    for (const gid of GUILD_IDS) {
      await rest.put(Routes.applicationGuildCommands(APP_ID, gid), { body: commands });
      console.log(`Registered commands for guild ${gid}`);
    }
  } else {
    await rest.put(Routes.applicationCommands(APP_ID), { body: commands });
    console.log('Registered commands globally');
  }
}

client.on('ready', () => {
  console.log(`Command bot logged in as ${client.user?.tag}`);
});

client.on('interactionCreate', async (interaction) => {
  if (!interaction.isChatInputCommand()) return;
  if (interaction.commandName !== 'notify') return;
  if (interaction.options.getSubcommand() !== 'set-channel') return;

  const up = db.prepare('INSERT INTO guild_settings(guild_id, channel_id) VALUES (?,?) ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id');
  up.run(interaction.guildId!, interaction.channelId);
  await interaction.reply({ content: `Notifications will be sent to <#${interaction.channelId}>`, ephemeral: true });
});

async function main() {
  await registerCommands();
  if (TOKEN) await client.login(TOKEN);
  else console.warn('DISCORD_TOKEN not set; command bot will not connect.');
}

main();
