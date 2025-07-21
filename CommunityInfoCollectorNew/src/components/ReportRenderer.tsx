import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Modal,
  StyleSheet,
  Linking,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';
import { logService } from '../services/log.service';

interface FootnoteLink {
  footnote_number: number;
  url: string;
  title: string;
  score: number;
  comments: number;
  subreddit: string;
  author: string;
  created_utc: string;
}

interface ReportRendererProps {
  fullReport: string;
  reportLinks?: FootnoteLink[];
  keywords?: Array<{
    keyword: string;
    translated_keyword?: string;
    posts_found: number;
    sample_titles: string[];
  }>;
  onClose?: () => void;
}

export default function ReportRenderer({ fullReport, reportLinks = [], keywords = [], onClose }: ReportRendererProps) {
  const [selectedFootnote, setSelectedFootnote] = useState<FootnoteLink | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  
  useEffect(() => {
    logService.info('ReportRenderer 마운트', {
      reportLinksCount: reportLinks.length,
      reportLength: fullReport?.length || 0
    });
    
    // reportLinks 데이터 검증
    if (reportLinks.length > 0) {
      reportLinks.forEach((link, index) => {
        logService.debug(`각주 링크 [${index}]`, {
          footnote_number: link.footnote_number,
          created_utc: link.created_utc,
          title: link.title?.substring(0, 50) + '...'
        });
      });
    }
  }, [reportLinks, fullReport]);

  // 각주 번호를 클릭 가능한 컴포넌트로 변환
  const renderTextWithFootnotes = (text: string) => {
    const footnotePattern = /\[(\d+)\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = footnotePattern.exec(text)) !== null) {
      // 각주 이전 텍스트
      if (match.index > lastIndex) {
        parts.push(
          <Text key={`text-${lastIndex}`}>
            {text.substring(lastIndex, match.index)}
          </Text>
        );
      }

      // 각주 번호
      const footnoteNumber = parseInt(match[1]);
      const footnoteLink = reportLinks.find(link => link.footnote_number === footnoteNumber);
      
      parts.push(
        <TouchableOpacity
          key={`footnote-${match.index}`}
          onPress={() => handleFootnotePress(footnoteLink)}
          style={styles.footnoteButton}
        >
          <Text style={styles.footnoteText}>{match[0]}</Text>
        </TouchableOpacity>
      );

      lastIndex = match.index + match[0].length;
    }

    // 마지막 텍스트
    if (lastIndex < text.length) {
      parts.push(
        <Text key={`text-${lastIndex}`}>
          {text.substring(lastIndex)}
        </Text>
      );
    }

    return parts;
  };

  const handleFootnotePress = (footnoteLink: FootnoteLink | undefined) => {
    try {
      logService.info('각주 클릭', {
        footnoteNumber: footnoteLink?.footnote_number,
        hasLink: !!footnoteLink
      });
      
      if (footnoteLink) {
        setSelectedFootnote(footnoteLink);
        setModalVisible(true);
        logService.debug('각주 모달 표시', {
          title: footnoteLink.title,
          created_utc: footnoteLink.created_utc,
          url: footnoteLink.url
        });
      } else {
        logService.warning('각주 링크를 찾을 수 없음');
      }
    } catch (error) {
      logService.error('각주 클릭 처리 오류', error);
    }
  };

  const handleOpenLink = () => {
    if (selectedFootnote?.url) {
      Linking.openURL(selectedFootnote.url);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      logService.debug('날짜 포맷팅 시도', { dateString });
      const date = new Date(dateString);
      
      // Invalid Date 체크
      if (isNaN(date.getTime())) {
        logService.error('유효하지 않은 날짜', { dateString });
        return '날짜 정보 없음';
      }
      
      return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (error) {
      logService.error('날짜 포맷팅 오류', { dateString, error });
      return '날짜 오류';
    }
  };

  // 마크다운 텍스트 파싱
  const parseMarkdown = (text: string) => {
    const elements = [];
    const lines = text.split('\n');
    let inBlockquote = false;
    let blockquoteContent = '';
    let inList = false;
    let listItems = [];
    
    lines.forEach((line, lineIndex) => {
      // 빈 줄 처리
      if (!line.trim()) {
        if (inBlockquote) {
          elements.push({ type: 'blockquote', content: blockquoteContent.trim() });
          inBlockquote = false;
          blockquoteContent = '';
        }
        if (inList) {
          elements.push({ type: 'list', items: listItems });
          inList = false;
          listItems = [];
        }
        return;
      }
      
      // H2 헤더 (##)
      if (line.startsWith('## ')) {
        elements.push({ type: 'h2', content: line.substring(3).trim() });
      }
      // H3 헤더 (###)
      else if (line.startsWith('### ')) {
        elements.push({ type: 'h3', content: line.substring(4).trim() });
      }
      // 인용문 (>)
      else if (line.startsWith('>')) {
        inBlockquote = true;
        blockquoteContent += line.substring(1).trim() + '\n';
      }
      // 리스트 (-, *)
      else if (line.startsWith('- ') || line.startsWith('* ')) {
        inList = true;
        listItems.push(line.substring(2).trim());
      }
      // 일반 텍스트
      else {
        if (inBlockquote) {
          elements.push({ type: 'blockquote', content: blockquoteContent.trim() });
          inBlockquote = false;
          blockquoteContent = '';
        }
        if (inList) {
          elements.push({ type: 'list', items: listItems });
          inList = false;
          listItems = [];
        }
        elements.push({ type: 'paragraph', content: line });
      }
    });
    
    // 마지막 요소 처리
    if (inBlockquote) {
      elements.push({ type: 'blockquote', content: blockquoteContent.trim() });
    }
    if (inList) {
      elements.push({ type: 'list', items: listItems });
    }
    
    return elements;
  };
  
  // 인라인 스타일 처리
  const renderInlineText = (text: string) => {
    // **bold**, *italic*, `code` 처리
    const parts = [];
    let currentText = text;
    
    // Bold 처리
    const boldRegex = /\*\*([^*]+)\*\*/g;
    let lastIndex = 0;
    let match;
    
    while ((match = boldRegex.exec(currentText)) !== null) {
      if (match.index > lastIndex) {
        parts.push(
          <Text key={`text-${lastIndex}`}>
            {renderTextWithFootnotes(currentText.substring(lastIndex, match.index))}
          </Text>
        );
      }
      parts.push(
        <Text key={`bold-${match.index}`} style={styles.boldText}>
          {renderTextWithFootnotes(match[1])}
        </Text>
      );
      lastIndex = match.index + match[0].length;
    }
    
    if (lastIndex < currentText.length) {
      parts.push(
        <Text key={`text-final`}>
          {renderTextWithFootnotes(currentText.substring(lastIndex))}
        </Text>
      );
    }
    
    return parts.length > 0 ? parts : renderTextWithFootnotes(text);
  };
  
  // 보고서를 섹션별로 렌더링
  const renderReport = () => {
    const elements = parseMarkdown(fullReport);
    
    return elements.map((element, index) => {
      switch (element.type) {
        case 'h2':
          return (
            <View key={`h2-${index}`} style={styles.section}>
              <Text style={styles.sectionTitle}>{element.content}</Text>
            </View>
          );
          
        case 'h3':
          return (
            <View key={`h3-${index}`} style={styles.subsection}>
              <Text style={styles.subsectionTitle}>{element.content}</Text>
            </View>
          );
          
        case 'blockquote':
          return (
            <View key={`quote-${index}`} style={styles.blockquote}>
              <Text style={styles.blockquoteText}>
                {renderInlineText(element.content)}
              </Text>
            </View>
          );
          
        case 'list':
          return (
            <View key={`list-${index}`} style={styles.list}>
              {element.items.map((item, itemIndex) => (
                <View key={`item-${itemIndex}`} style={styles.listItem}>
                  <Text style={styles.listBullet}>•</Text>
                  <Text style={styles.listItemText}>
                    {renderInlineText(item)}
                  </Text>
                </View>
              ))}
            </View>
          );
          
        case 'paragraph':
          return (
            <View key={`para-${index}`} style={styles.paragraph}>
              <Text style={styles.paragraphText}>
                {renderInlineText(element.content)}
              </Text>
            </View>
          );
          
        default:
          return null;
      }
    });
  };

  return (
    <View style={styles.container}>
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        <View style={styles.content}>
          {renderReport()}
          
          {/* 정보 수집 과정 표시 */}
          {keywords && keywords.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>정보 수집 과정</Text>
              <View style={styles.keywordsContainer}>
                <Text style={styles.subsectionTitle}>사용된 키워드</Text>
                {keywords.map((kw, index) => (
                  <View key={index} style={styles.keywordItem}>
                    <View style={styles.keywordHeader}>
                      <Text style={styles.keywordText}>
                        {index + 1}. {kw.keyword}
                        {kw.translated_keyword && ` → ${kw.translated_keyword}`}
                      </Text>
                      <Text style={styles.postsFoundText}>
                        {kw.posts_found}개 게시물
                      </Text>
                    </View>
                    {kw.sample_titles && kw.sample_titles.length > 0 && (
                      <View style={styles.sampleTitles}>
                        {kw.sample_titles.map((title, titleIndex) => (
                          <Text key={titleIndex} style={styles.sampleTitle} numberOfLines={1}>
                            • {title}
                          </Text>
                        ))}
                      </View>
                    )}
                  </View>
                ))}
              </View>
            </View>
          )}
        </View>
      </ScrollView>

      {/* 각주 상세 정보 모달 */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={modalVisible}
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            {selectedFootnote && (
              <>
                <View style={styles.modalHeader}>
                  <Text style={styles.modalTitle}>참조 [{selectedFootnote.footnote_number}]</Text>
                  <TouchableOpacity
                    onPress={() => setModalVisible(false)}
                    style={styles.closeButton}
                  >
                    <Text style={styles.closeButtonText}>✕</Text>
                  </TouchableOpacity>
                </View>

                <ScrollView style={styles.modalBody}>
                  <Text style={styles.postTitle}>{selectedFootnote.title}</Text>
                  
                  <View style={styles.postMeta}>
                    <Text style={styles.metaText}>
                      r/{selectedFootnote.subreddit} • u/{selectedFootnote.author}
                    </Text>
                    <Text style={styles.metaText}>
                      {formatDate(selectedFootnote.created_utc)}
                    </Text>
                  </View>

                  <View style={styles.postStats}>
                    <View style={styles.statItem}>
                      <Text style={styles.statValue}>{selectedFootnote.score}</Text>
                      <Text style={styles.statLabel}>점수</Text>
                    </View>
                    <View style={styles.statItem}>
                      <Text style={styles.statValue}>{selectedFootnote.comments}</Text>
                      <Text style={styles.statLabel}>댓글</Text>
                    </View>
                  </View>

                  <TouchableOpacity
                    style={styles.openLinkButton}
                    onPress={handleOpenLink}
                  >
                    <Text style={styles.openLinkButtonText}>원본 게시물 보기</Text>
                  </TouchableOpacity>
                </ScrollView>
              </>
            )}
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 20,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1C1C1E',
    marginBottom: 12,
  },
  subsection: {
    marginBottom: 16,
  },
  subsectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1C1C1E',
    marginBottom: 8,
  },
  paragraph: {
    marginBottom: 16,
  },
  paragraphText: {
    fontSize: 15,
    lineHeight: 22,
    color: '#3C3C43',
  },
  footnoteButton: {
    marginHorizontal: 2,
  },
  footnoteText: {
    color: '#007AFF',
    fontSize: 15,
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  boldText: {
    fontWeight: 'bold',
  },
  blockquote: {
    marginVertical: 12,
    paddingLeft: 16,
    borderLeftWidth: 4,
    borderLeftColor: '#007AFF',
    backgroundColor: '#F2F2F7',
    padding: 12,
    borderRadius: 8,
  },
  blockquoteText: {
    fontSize: 14,
    lineHeight: 20,
    color: '#3C3C43',
    fontStyle: 'italic',
  },
  list: {
    marginVertical: 8,
  },
  listItem: {
    flexDirection: 'row',
    marginBottom: 8,
    paddingLeft: 8,
  },
  listBullet: {
    fontSize: 15,
    color: '#3C3C43',
    marginRight: 8,
    width: 20,
  },
  listItemText: {
    flex: 1,
    fontSize: 15,
    lineHeight: 22,
    color: '#3C3C43',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '70%',
    paddingBottom: 34, // Safe area bottom
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1C1C1E',
  },
  closeButton: {
    padding: 8,
  },
  closeButtonText: {
    fontSize: 24,
    color: '#8E8E93',
  },
  modalBody: {
    padding: 20,
  },
  postTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#1C1C1E',
    marginBottom: 12,
    lineHeight: 22,
  },
  postMeta: {
    marginBottom: 16,
  },
  metaText: {
    fontSize: 13,
    color: '#8E8E93',
    marginBottom: 4,
  },
  postStats: {
    flexDirection: 'row',
    marginBottom: 20,
    paddingVertical: 16,
    backgroundColor: '#F2F2F7',
    borderRadius: 12,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1C1C1E',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 13,
    color: '#8E8E93',
  },
  openLinkButton: {
    backgroundColor: '#007AFF',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  openLinkButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  keywordsContainer: {
    backgroundColor: '#F2F2F7',
    borderRadius: 12,
    padding: 16,
    marginTop: 8,
  },
  keywordItem: {
    marginBottom: 16,
  },
  keywordHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  keywordText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1C1C1E',
    flex: 1,
  },
  postsFoundText: {
    fontSize: 13,
    color: '#8E8E93',
    marginLeft: 8,
  },
  sampleTitles: {
    marginLeft: 20,
  },
  sampleTitle: {
    fontSize: 12,
    color: '#8E8E93',
    marginBottom: 4,
    lineHeight: 16,
  },
});