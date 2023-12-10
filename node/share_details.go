package node

import (
	"context"
	"encoding/json"
	"fmt"
	"path/filepath"
	"io/ioutil"
	"os"
	"github.com/libp2p/go-libp2p-core/peer"
	pubsub "github.com/libp2p/go-libp2p-pubsub"
)

// Represents the default fallback room and user names
// if they aren't provided when the app is started
const room = "connection"
const chat_location = "/home/johny/test_projects/peerchat/chat"

// A structure that represents a PubSub Chat Room
type ChatRoom struct {
	// Represents the P2P Host for the ChatRoom
	Host *P2P

	// Represents the channel of incoming messages
	Inbound chan chatmessage
	// Represents the channel of outgoing messages
	Outbound chan string
	// Represents the channel of chat log messages
	Logs chan chatlog

	// Represents the name of the chat room
	RoomName string
	// Represent the name of the user in the chat room
	UserName string
	// Represents the host ID of the peer
	selfid peer.ID

	// Represents the chat room lifecycle context
	psctx context.Context
	// Represents the chat room lifecycle cancellation function
	pscancel context.CancelFunc
	// Represents the PubSub Topic of the ChatRoom
	pstopic *pubsub.Topic
	// Represents the PubSub Subscription for the topic
	psub *pubsub.Subscription
	IP   string // ip of message database
    Port string // port of message database
	Key string 	// The public key of the module
	Module_Name string // The name of the module
	Signature string // message needs to be signed with the modules key
}

// A structure that represents a chat message
type chatmessage struct {
	Message    string `json:"message"`
	SenderID   string `json:"senderid"`
    IP   string `json:"ip"`
    Port string `json:"port"`
	Key string `json:"key"`
	Module_Name string `json:"module_name"`
	Signature string `json:"signature"`
}


// A structure that represents a chat log
type chatlog struct {
	logprefix string
	logmsg    string
}

// A constructor function that generates and returns a new
// ChatRoom for a given P2PHost, username and roomname
func JoinChatRoom(p2phost *P2P, username string, roomname string) (*ChatRoom, error) {

	// Create a PubSub topic with the room name
	topic, err := p2phost.PubSub.Join(fmt.Sprintf("room-peerchat-%s", roomname))
	// Check the error
	if err != nil {
		return nil, err
	}

	// Subscribe to the PubSub topic
	sub, err := topic.Subscribe()
	// Check the error
	if err != nil {
		return nil, err
	}


	// Check the provided roomname
	if roomname == "" {
		// Use the default room name
		roomname = room
	}

	// Create cancellable context
	pubsubctx, cancel := context.WithCancel(context.Background())

	// Create a ChatRoom object
	chatroom := &ChatRoom{
		Host: p2phost,

		Inbound:  make(chan chatmessage),
		Outbound: make(chan string),
		Logs:     make(chan chatlog),

		psctx:    pubsubctx,
		pscancel: cancel,
		pstopic:  topic,
		psub:     sub,

		RoomName: roomname,
		UserName: username,
		selfid:   p2phost.Host.ID(),
	}

	// // Start the subscribe loop
	go chatroom.SubLoop()
	// // Start the publish loop
	go chatroom.PubLoop()

	// Return the chatroom
	return chatroom, nil
}

// A method of ChatRoom that publishes a chatmessage
// to the PubSub topic until the pubsub context closes
func (cr *ChatRoom) PubLoop() {
	for {
		select {
		case <-cr.psctx.Done():
			return

		case message := <-cr.Outbound:
			// Create a ChatMessage
			m := chatmessage{
                
                    Message:    message,
                    SenderID:   cr.selfid.Pretty(),
					IP:   cr.IP,
					Port: cr.Port,
					Signature: cr.Signature,
            }

			// Marshal the ChatMessage into a JSON
			messagebytes, err := json.Marshal(m)
			if err != nil {
				cr.Logs <- chatlog{logprefix: "puberr", logmsg: "could not marshal JSON"}
				continue
			}

			// Publish the message to the topic
			err = cr.pstopic.Publish(cr.psctx, messagebytes)
			if err != nil {
				cr.Logs <- chatlog{logprefix: "puberr", logmsg: "could not publish to topic"}
				continue
			}
		}
	}
}


const maxMessages = 100
const storageDir = "node/chat"
const storageFile = "messages.json"

func saveChatMessage(cm chatmessage) error {
	// Construct file path
	filePath := filepath.Join(storageDir, storageFile)

	// Read existing messages
	var messages []chatmessage
	data, err := ioutil.ReadFile(filePath)
	if err != nil && !os.IsNotExist(err) {
		return err
	}
	if len(data) > 0 {
		err = json.Unmarshal(data, &messages)
		if err != nil {
			return err
		}
	}

	// Append new message
	messages = append(messages, cm)

	// Keep only the last maxMessages messages
	if len(messages) > maxMessages {
		messages = messages[len(messages)-maxMessages:]
	}

	// Save updated messages
	newData, err := json.MarshalIndent(messages, "", "    ")
	if err != nil {
		return err
	}
	return ioutil.WriteFile(filePath, newData, 0644)
}


// A method of ChatRoom that continously reads from the subscription
// until either the subscription or pubsub context closes.
// The recieved message is parsed sent into the inbound channel
func (cr *ChatRoom) SubLoop() {
	// Start loop
	for {
		select {
		case <-cr.psctx.Done():
			return

		default:
			// Read a message from the subscription
			message, err := cr.psub.Next(cr.psctx)
			// Check error
			if err != nil {
				// Close the messages queue (subscription has closed)
				close(cr.Inbound)
				cr.Logs <- chatlog{logprefix: "suberr", logmsg: "subscription has closed"}
				return
			}

			// Check if message is from self
			if message.ReceivedFrom == cr.selfid {
				continue
			}
			
			
			
			// Declare a ChatMessage
			cm := &chatmessage{}
			// Unmarshal the message data into a ChatMessage
			err = json.Unmarshal(message.Data, cm)
			if err != nil {
				cr.Logs <- chatlog{logprefix: "suberr", logmsg: "could not unmarshal JSON"}
				continue
			}
			
		
			// Send the ChatMessage into the message queue
			cr.Inbound <- *cm
			
			// Save the message
			err = saveChatMessage(*cm)
			if err != nil {
				// Handle error, maybe log it
			}
		}
	}
}
