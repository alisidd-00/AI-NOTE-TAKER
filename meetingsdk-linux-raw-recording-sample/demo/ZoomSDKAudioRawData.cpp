//GetAudioRawData
#include "rawdata/rawdata_audio_helper_interface.h"
#include "ZoomSDKAudioRawData.h"
#include "zoom_sdk_def.h" 
#include <iostream>
#include <fstream>

std::string getMeetingID(const std::string& configFilePath) {
    std::ifstream configFile(configFilePath);
    std::string line;
    std::string meetingIDPrefix = "meeting_number: \"";
    std::string meetingID = "";

    if (configFile.is_open()) {
        while (getline(configFile, line)) {
            auto prefixPos = line.find(meetingIDPrefix);
            if (prefixPos != std::string::npos) {
                // Found the meeting number line
                meetingID = line.substr(prefixPos + meetingIDPrefix.length());
                // Remove the last quote
                meetingID.erase(meetingID.length() - 1);
                break;
            }
        }
        configFile.close();
    } else {
        std::cout << "Unable to open config file: " << configFilePath << std::endl;
    }
    
    return meetingID;
}

void ZoomSDKAudioRawData::onOneWayAudioRawDataReceived(AudioRawData* audioRawData, uint32_t node_id)
{
	//std::cout << "Received onOneWayAudioRawDataReceived" << std::endl;
	//add your code here
}

void ZoomSDKAudioRawData::onMixedAudioRawDataReceived(AudioRawData* audioRawData)
{
	std::cout << "Received onMixedAudioRawDataReceived" << std::endl;
	static std::ofstream pcmFile;
	std::string meetingID = getMeetingID("/app/demo/config.txt");

	std::string filePath = "/app/recordings/" +meetingID+ ".pcm";

	pcmFile.open(filePath, std::ios::out | std::ios::binary | std::ios::app);

	if (!pcmFile.is_open()) {
		std::cout << "Failed to open wave file" << std::endl;
		return;
	}
	
		// Write the audio data to the file
		pcmFile.write((char*)audioRawData->GetBuffer(), audioRawData->GetBufferLen());
		//std::cout << "buffer length: " << audioRawData->GetBufferLen() << std::endl;
		std::cout << "buffer : " << audioRawData->GetBuffer() << std::endl;

		// Close the wave file
		pcmFile.close();
		pcmFile.flush();
}

void ZoomSDKAudioRawData::onShareAudioRawDataReceived(AudioRawData* data_)
{
}