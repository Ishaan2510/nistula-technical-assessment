-- =============================================================
-- NISTULA UNIFIED MESSAGING PLATFORM — POSTGRESQL SCHEMA
-- =============================================================
-- Design principles:
--   1. One canonical guest record per real-world person, regardless
--      of how many channels they use. Identity resolution handled
--      via guest_channel_identities.
--   2. All messages — inbound and outbound, across all channels —
--      live in one table. Direction column separates them.
--   3. AI metadata (confidence score, query type, drafted reply)
--      stored directly on the message row. No separate AI log table —
--      the message IS the unit of work.
--   4. send_status tracks the full lifecycle of an outbound message:
--      ai_drafted -> agent_edited -> auto_sent | escalated.
-- =============================================================


-- -------------------------------------------------------------
-- GUESTS
-- One record per real-world guest. Email and phone are nullable
-- because the first contact may come through a channel that
-- does not expose them (e.g. Instagram DM).
-- -------------------------------------------------------------
CREATE TABLE guests (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name   VARCHAR(255) NOT NULL,
    email       VARCHAR(255),
    phone       VARCHAR(50),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- -------------------------------------------------------------
-- GUEST CHANNEL IDENTITIES
-- Solves the hardest design problem: a guest who books on Airbnb,
-- messages on WhatsApp, and follows on Instagram is three different
-- IDs on three different platforms but one person. This table maps
-- each (channel, channel_guest_id) pair to a canonical guest.
--
-- Design decision: UNIQUE constraint on (channel, channel_guest_id)
-- ensures we never create duplicate identity records. The application
-- layer is responsible for identity resolution (e.g. matching by
-- phone number when a new channel identity comes in).
-- -------------------------------------------------------------
CREATE TABLE guest_channel_identities (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guest_id              UUID NOT NULL REFERENCES guests(id) ON DELETE CASCADE,
    channel               VARCHAR(50) NOT NULL,       -- whatsapp, airbnb, booking_com, instagram, direct
    channel_guest_id      VARCHAR(255) NOT NULL,      -- platform-specific identifier
    channel_display_name  VARCHAR(255),               -- name as it appears on that channel
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(channel, channel_guest_id)
);


-- -------------------------------------------------------------
-- PROPERTIES
-- Stores villa/property details. property_id is a human-readable
-- slug (e.g. 'villa-b1') rather than a UUID because it is used
-- as a foreign key from external webhook payloads.
-- -------------------------------------------------------------
CREATE TABLE properties (
    id                  VARCHAR(50) PRIMARY KEY,       -- e.g. 'villa-b1'
    name                VARCHAR(255) NOT NULL,
    location            VARCHAR(255),
    max_guests          INT,
    base_rate_inr       NUMERIC(10, 2),
    extra_guest_rate_inr NUMERIC(10, 2),
    check_in_time       TIME DEFAULT '14:00',
    check_out_time      TIME DEFAULT '11:00',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- -------------------------------------------------------------
-- RESERVATIONS
-- One record per booking. Linked to a canonical guest and a property.
-- source_channel records where the booking originated (Airbnb, direct, etc.)
-- booking_ref is the human-readable ID (e.g. NIS-2024-0891).
-- -------------------------------------------------------------
CREATE TABLE reservations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_ref      VARCHAR(50) UNIQUE,
    guest_id         UUID REFERENCES guests(id),
    property_id      VARCHAR(50) REFERENCES properties(id),
    check_in         DATE NOT NULL,
    check_out        DATE NOT NULL,
    num_guests       INT,
    total_amount_inr NUMERIC(10, 2),
    status           VARCHAR(50) NOT NULL DEFAULT 'confirmed',  -- confirmed, cancelled, completed, no_show
    source_channel   VARCHAR(50),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- -------------------------------------------------------------
-- CONVERSATIONS
-- A conversation groups all messages in a single thread between
-- a guest and Nistula on a given channel.
--
-- Design decision: a guest can have multiple conversations (one
-- per booking, or one for a general enquiry before booking).
-- reservation_id is nullable because pre-sales conversations
-- exist before a booking is created.
--
-- status tracks whether the thread is resolved or needs attention.
-- -------------------------------------------------------------
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guest_id        UUID REFERENCES guests(id),
    reservation_id  UUID REFERENCES reservations(id),   -- nullable: pre-booking enquiries have no reservation yet
    property_id     VARCHAR(50) REFERENCES properties(id),
    channel         VARCHAR(50) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'open',  -- open, resolved, escalated, pending_human
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- -------------------------------------------------------------
-- MESSAGES
-- Every inbound and outbound message across all channels in one table.
-- direction = 'inbound' for guest messages, 'outbound' for Nistula replies.
--
-- AI metadata columns are populated for inbound messages only:
--   query_type:        classification result
--   ai_confidence_score: 0.000 to 1.000
--   ai_drafted_reply:  the text Claude produced
--
-- Outbound tracking columns track what actually happened to the reply:
--   send_status:  ai_drafted | agent_edited | auto_sent | escalated
--   sent_by:      NULL if auto_sent, agent_id if a human edited/approved
--   sent_at:      when the message was actually delivered to the guest
--
-- channel_message_id stores the ID from the source platform (e.g.
-- WhatsApp message ID, Airbnb thread ID) for deduplication.
-- -------------------------------------------------------------
CREATE TABLE messages (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id       UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    direction             VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),

    -- Core content
    message_text          TEXT NOT NULL,
    channel               VARCHAR(50) NOT NULL,

    -- Inbound: classification and AI metadata
    query_type            VARCHAR(50),           -- populated for inbound messages
    ai_confidence_score   NUMERIC(4, 3),         -- 0.000 to 1.000
    ai_drafted_reply      TEXT,                  -- what Claude produced for this inbound message

    -- Outbound: lifecycle tracking
    send_status           VARCHAR(50),           -- ai_drafted | agent_edited | auto_sent | escalated
    sent_by               UUID,                  -- FK to an agents/users table (not in scope here)
    sent_at               TIMESTAMPTZ,

    -- Channel deduplication
    channel_message_id    VARCHAR(255),          -- platform-assigned message ID

    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- =============================================================
-- INDEXES
-- Chosen for the most common access patterns:
--   - Load all messages in a conversation (messages page)
--   - Look up conversations by guest (guest profile view)
--   - Look up conversations by reservation (booking detail view)
--   - Resolve a channel identity to a canonical guest (webhook ingestion)
--   - Find a reservation by booking_ref (webhook payload lookup)
--   - Filter messages by query type (analytics / reporting)
-- =============================================================
CREATE INDEX idx_messages_conversation      ON messages(conversation_id);
CREATE INDEX idx_messages_query_type        ON messages(query_type);
CREATE INDEX idx_messages_send_status       ON messages(send_status);
CREATE INDEX idx_conversations_guest        ON conversations(guest_id);
CREATE INDEX idx_conversations_reservation  ON conversations(reservation_id);
CREATE INDEX idx_conversations_status       ON conversations(status);
CREATE INDEX idx_guest_identities_lookup    ON guest_channel_identities(channel, channel_guest_id);
CREATE INDEX idx_reservations_booking_ref   ON reservations(booking_ref);
CREATE INDEX idx_reservations_guest         ON reservations(guest_id);