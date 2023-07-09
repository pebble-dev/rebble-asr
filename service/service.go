package service

import (
	speech "cloud.google.com/go/speech/apiv1"
	"cloud.google.com/go/speech/apiv1/speechpb"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"google.golang.org/api/option"
	"google.golang.org/protobuf/types/known/wrapperspb"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"strings"
	"time"
)

type Service struct {
	mux    *http.ServeMux
	client *http.Client
	speech *speech.Client
}

func New() *Service {
	sc, err := speech.NewClient(context.Background(),
		option.WithAPIKey("some key"))
	if err != nil {
		panic(fmt.Sprintf("speech startup failed: %s!", err))
	}
	s := &Service{
		mux: http.NewServeMux(),
		client: &http.Client{
			Timeout: 5 * time.Second,
		},
		speech: sc,
	}
	s.mux.HandleFunc("/NmspServlet/", s.nmsp)
	return s
}

func (s *Service) Close() error {
	return s.speech.Close()
}

func (s *Service) nmsp(rw http.ResponseWriter, request *http.Request) {
	accessToken, lang, err := tokensFromHost(request.Host)
	if err != nil {
		http.Error(rw, err.Error(), http.StatusBadRequest)
		return
	}
	if err := s.authenticate(accessToken, request.Context()); err != nil {
		http.Error(rw, err.Error(), http.StatusUnauthorized)
		return
	}

	reader, err := request.MultipartReader()
	if err != nil {
		http.Error(rw, fmt.Sprintf("failed to open reader: %s", err), 400)
		return
	}

	// start an async request to ASR
	rec, err := s.speech.StreamingRecognize(request.Context())
	if err != nil {
		http.Error(rw, fmt.Sprintf("starting speech recognition failed: %s", err), http.StatusInternalServerError)
	}

	err = rec.Send(&speechpb.StreamingRecognizeRequest{
		StreamingRequest: &speechpb.StreamingRecognizeRequest_StreamingConfig{
			StreamingConfig: &speechpb.StreamingRecognitionConfig{
				Config: &speechpb.RecognitionConfig{
					Encoding:                   speechpb.RecognitionConfig_SPEEX_WITH_HEADER_BYTE,
					SampleRateHertz:            16000,
					AudioChannelCount:          1,
					LanguageCode:               lang,
					MaxAlternatives:            1,
					ProfanityFilter:            false,
					EnableWordTimeOffsets:      false,
					EnableWordConfidence:       true, // this gets passed all the way to Pebble, which does nothing?
					EnableAutomaticPunctuation: true, // controversial.
					EnableSpokenPunctuation:    wrapperspb.Bool(true),
					EnableSpokenEmojis:         wrapperspb.Bool(false), // tentatively disabled due to poor font support.
					Metadata: &speechpb.RecognitionMetadata{
						MicrophoneDistance: speechpb.RecognitionMetadata_NEARFIELD,
					},
					Model:       "latest_short", // apparently this is the New Hotness
					UseEnhanced: false,
				},
				SingleUtterance:           false, // end-of-utterance detection is done by Pebble
				InterimResults:            false, // the pebble protocol doesn't have any way to deal with these
				EnableVoiceActivityEvents: false, // we don't need this
				VoiceActivityTimeout:      nil,   // again, handled by the Pebble device.
			},
		},
	})
	if err != nil {
		http.Error(rw, fmt.Sprintf("setting up dictation session failed: %s", err), http.StatusInternalServerError)
		return
	}

	go func() {
		for {
			part, err := reader.NextPart()
			if err == io.EOF {
				break
			}
			if err != nil {
				break
			}
			if part.FormName() == "ConcludingAudioParameter" {
				bytes, err := io.ReadAll(part)
				if err != nil {
					// TODO: something?
					break
				}
				err = rec.Send(&speechpb.StreamingRecognizeRequest{
					StreamingRequest: &speechpb.StreamingRecognizeRequest_AudioContent{
						AudioContent: bytes,
					},
				})
				if err != nil {
					// TODO: something?
					break
				}
			}
		}
	}()

	mp := multipart.NewWriter(rw)
	must(mp.SetBoundary("--Nuance_NMSP_vutc5w1XobDdefsYG3wq"))
	rw.Header().Set("Content-Type", "multipart/form-data; boundary="+mp.Boundary())
	rw.WriteHeader(200)

	firstWord := true

	for {
		resp, err := rec.Recv()
		if err == io.EOF {
			break
		}

		tr := TranscriptionResponse{}

		for _, result := range resp.Results {
			if len(result.Alternatives) == 0 {
				continue
			}
			for _, word := range result.Alternatives[0].Words {
				tr.Words = append(tr.Words, TranscriptionWord{
					Word:       word.Word,
					Confidence: word.Confidence,
				})
			}
		}

		if firstWord && len(tr.Words) > 0 {
			tr.Words[0].Word = tr.Words[0].Word + `\*no-space-before`
			firstWord = false
		}

		content, err := json.Marshal(tr)
		if err != nil {
			log.Printf("Failed to marshal response JSON: %s", err)
			continue
		}

		if err := mp.WriteField("QueryResult", string(content)); err != nil {
			log.Printf("Failed to write response JSON: %s", err)
			continue
		}
	}
	_ = mp.Close()
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}

type TranscriptionWord struct {
	Word       string  `json:"word"`
	Confidence float32 `json:"confidence"`
}

type TranscriptionResponse struct {
	Words []TranscriptionWord `json:"words"`
}

func (s *Service) authenticate(accessToken string, ctx context.Context) error {
	authReq, err := http.NewRequestWithContext(ctx, "GET", "%s/api/v1/me/token", nil)
	if err != nil {
		return fmt.Errorf("couldn't create auth request: %w", err)
	}
	authReq.Header.Add("Authorization", "Bearer "+accessToken)
	resp, err := s.client.Do(authReq)
	if err != nil {
		return fmt.Errorf("requesting authorization failed: %w", err)
	}
	if resp.StatusCode != 200 {
		return errors.New("unauthorised")
	}
	return nil
}

func tokensFromHost(host string) (accessToken, lang string, err error) {
	hostParts := strings.SplitN(strings.SplitN(host, ".", 2)[0], "-", 2)
	if len(hostParts) != 2 {
		return "", "", fmt.Errorf("invalid host %q", host)
	}
	return hostParts[0], hostParts[1], nil
}

func (s *Service) ListenAndServe(addr string) error {
	return http.ListenAndServe(addr, s.mux)
}
