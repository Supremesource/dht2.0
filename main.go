package main

import (
	"bufio"
	"strings"
	"context"
	host "github.com/libp2p/go-libp2p-host"
	"github.com/libp2p/go-libp2p-kad-dht"
	// "github.com/libp2p/go-libp2p-core/peer"
	"flag"
	"fmt"
	// "log"
	"os"
	discovery "github.com/libp2p/go-libp2p-discovery"
	pubsub "github.com/libp2p/go-libp2p-pubsub"

	"time"
	"commune_chat/node"
	"github.com/sirupsen/logrus"
)

const figlet = `
 ██████╗ ██████╗ ███╗   ███╗███╗   ███╗██╗   ██╗███╗   ██╗███████╗
██╔════╝██╔═══██╗████╗ ████║████╗ ████║██║   ██║████╗  ██║██╔════╝
██║     ██║   ██║██╔████╔██║██╔████╔██║██║   ██║██╔██╗ ██║█████╗  
██║     ██║   ██║██║╚██╔╝██║██║╚██╔╝██║██║   ██║██║╚██╗██║██╔══╝  
╚██████╗╚██████╔╝██║ ╚═╝ ██║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║███████╗
 ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝
                                                                  
 ██████╗██╗  ██╗ █████╗ ████████╗                                 
██╔════╝██║  ██║██╔══██╗╚══██╔══╝                                 
██║     ███████║███████║   ██║                                    
██║     ██╔══██║██╔══██║   ██║                                    
╚██████╗██║  ██║██║  ██║   ██║                                    
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝                                                                                                                             																																																												  
`

func init() {
	// Log as Text with color
	logrus.SetFormatter(&logrus.TextFormatter{
		ForceColors:     true,
		FullTimestamp:   true,
		TimestampFormat: time.RFC822,
	})

	// Log to stdout
	logrus.SetOutput(os.Stdout)
}

type P2P struct {
	Ctx       context.Context
	Host      host.Host
	KadDHT    *dht.IpfsDHT
	Discovery *discovery.RoutingDiscovery
	PubSub    *pubsub.PubSub
}


	
func main() {
	// Define input flags
	username := flag.String("user", "", "username to use in the chatroom.")
	chatroom := flag.String("room", "", "chatroom to join.")
	ip := flag.String("ip", "127.0.0.1", "IP address for the chat application.")
	port := flag.String("port", "8080", "Port for the chat application.")


	// discovery := flag.String("discover", "", "method to use for discovery.")
	// Parse input flags
	flag.Parse()

	// Set the log level
	

	// Display the welcome figlet
	// fmt.Println(figlet)
	fmt.Println("The commune Application is starting.")
	fmt.Println("This may take upto 30 seconds.")
	fmt.Println()

	// Create a new P2PHost
	p2phost := node.NewP2P()
	fmt.Printf("%+v\n", p2phost)

	// Join the chat room
	chatapp, _ := node.JoinChatRoom(p2phost, *username, *chatroom)
	logrus.Infof("Joined the '%s' chatroom as '%s'", chatapp.RoomName, chatapp.UserName)

	chatapp.IP = *ip // placeholder IP
	chatapp.Port = *port  // placeholder Port
	chatapp.Signature = "dummySIG" // placeholder Signature
	chatapp.Key = "dummyKEY" // placeholder Key
	chatapp.Module_Name = "dummyModule" // placeholder Module_Name
	
	go func() {
        for msg := range chatapp.Inbound {
            fmt.Print("\nNew message: \n", msg.Message, "\n")
			fmt.Print("\nIP: ", msg.IP, "\n")
			fmt.Print("\nPort: ", msg.Port, "\n")
			

        }
    }()

    // Goroutine for sending messages
    go func() {
        reader := bufio.NewReader(os.Stdin)
        for {
            fmt.Print("Enter message: ")
            text, _ := reader.ReadString('\n')
            text = strings.TrimSpace(text)
            chatapp.Outbound <- text
        }
    }()

    // Prevent the main function from exiting
    select {}
}

// HISTORY SOLUTION
// save last 100 messages into a file
// provide an api to get the last 100 messages
// if you don't have any chat history contact the ip and port to get the chat history
// verify the signature of each message in the chat history
	
