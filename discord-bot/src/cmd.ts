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
      .addSubcommand(sc => sc
        .setName('subscribe')
        .setDescription('Subscribe this server to a calendar')
        .addStringOption(o => o.setName('calendar_id').setDescription('Calendar ID').setRequired(true)))
      .addSubcommand(sc => sc
        .setName('unsubscribe')
        .setDescription('Unsubscribe this server from a calendar')
        .addStringOption(o => o.setName('calendar_id').setDescription('Calendar ID').setRequired(true)))
      .addSubcommand(sc => sc
        .setName('list')
        .setDescription('List subscriptions and available calendars'))
      .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
      .toJSON()
  ];

  const rest = new REST({ version: '10' }).setToken(TOKEN);

  if (GUILD_IDS.length > 0) {
    for (const gid of GUILD_IDS) {
      await rest.put(Routes.applicationGuildCommands(APP_ID, gid), { body: commands });
      console.log(`Registered ${commands.length} command set(s) for guild ${gid}`);
    }
  } else {
    await rest.put(Routes.applicationCommands(APP_ID), { body: commands });
    console.log(`Registered ${commands.length} command set(s) globally`);
  }
}

client.on('ready', () => {
  console.log(`Command bot logged in as ${client.user?.tag}`);
});

client.on('interactionCreate', async (interaction) => {
  if (!interaction.isChatInputCommand()) return;
  if (interaction.commandName !== 'notify') return;

  const sub = interaction.options.getSubcommand();
  if (sub === 'set-channel') {
    const up = db.prepare('INSERT INTO guild_settings(guild_id, channel_id) VALUES (?,?) ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id');
    up.run(interaction.guildId!, interaction.channelId);
    await interaction.reply({ content: `Notifications will be sent to <#${interaction.channelId}>`, ephemeral: true });
    return;
  }
  if (sub === 'subscribe') {
    const input = interaction.options.getString('calendar_id', true);
    const row = db.prepare('SELECT calendar_id, COALESCE(name, calendar_id) AS name FROM calendars WHERE calendar_id = ? OR name = ?').get(input, input) as { calendar_id: string; name: string } | undefined;
    const cal = row?.calendar_id ?? input;
    const name = row?.name ?? input;
    db.prepare('INSERT OR IGNORE INTO guild_calendar_subscriptions(guild_id, calendar_id) VALUES (?,?)').run(interaction.guildId!, cal);
    await interaction.reply({ content: `Subscribed to ${name}.`, ephemeral: true });
    return;
  }
  if (sub === 'unsubscribe') {
    const input = interaction.options.getString('calendar_id', true);
    const row = db.prepare('SELECT calendar_id, COALESCE(name, calendar_id) AS name FROM calendars WHERE calendar_id = ? OR name = ?').get(input, input) as { calendar_id: string; name: string } | undefined;
    const cal = row?.calendar_id ?? input;
    const name = row?.name ?? input;
    db.prepare('DELETE FROM guild_calendar_subscriptions WHERE guild_id = ? AND calendar_id = ?').run(interaction.guildId!, cal);
    await interaction.reply({ content: `Unsubscribed from ${name}.`, ephemeral: true });
    return;
  }
  if (sub === 'list') {
    const subs = db.prepare('SELECT COALESCE(c.name, gcs.calendar_id) AS name FROM guild_calendar_subscriptions gcs LEFT JOIN calendars c ON c.calendar_id = gcs.calendar_id WHERE gcs.guild_id = ?').all(interaction.guildId!) as { name: string }[];
    const cals = db.prepare('SELECT COALESCE(name, calendar_id) as name FROM calendars ORDER BY name').all() as { name: string }[];
    const subsText = subs.length ? subs.map(s => `${s.name}`).join(', ') : 'none';
    const availText = cals.length ? cals.map(c => `${c.name}`).join('\n') : 'none';
    const text = `Subscriptions: ${subsText}\nAvailable calendars:\n${availText}`;
    await interaction.reply({ content: text, ephemeral: true });
    return;
  }
});

async function main() {
  await registerCommands();
  if (TOKEN) await client.login(TOKEN);
  else console.warn('DISCORD_TOKEN not set; command bot will not connect.');
}

main();
